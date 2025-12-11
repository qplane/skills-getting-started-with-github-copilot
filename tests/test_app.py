"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        activity: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for activity, details in activities.items()
    }
    
    yield
    
    # Restore original state
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Test suite for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_get_activities_contains_required_fields(self, client, reset_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details

    def test_chess_club_has_correct_data(self, client, reset_activities):
        """Test Chess Club has correct initial data"""
        response = client.get("/activities")
        data = response.json()
        chess = data["Chess Club"]
        
        assert chess["description"] == "Learn strategies and compete in chess tournaments"
        assert chess["max_participants"] == 12
        assert "michael@mergington.edu" in chess["participants"]
        assert "daniel@mergington.edu" in chess["participants"]


class TestSignupForActivity:
    """Test suite for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client, reset_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert "newstudent@mergington.edu" in participants

    def test_signup_for_nonexistent_activity(self, client, reset_activities):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test signing up a participant who is already signed up"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_participants(self, client, reset_activities):
        """Test signing up multiple different participants"""
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        response1 = client.post(f"/activities/Programming Class/signup?email={email1}")
        response2 = client.post(f"/activities/Programming Class/signup?email={email2}")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both were added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Programming Class"]["participants"]
        assert email1 in participants
        assert email2 in participants

    def test_signup_preserves_existing_participants(self, client, reset_activities):
        """Test that signup preserves existing participants"""
        original_response = client.get("/activities")
        original_participants = original_response.json()["Tennis Club"]["participants"].copy()
        
        response = client.post(
            "/activities/Tennis Club/signup?email=newtennis@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify original participants are still there
        updated_response = client.get("/activities")
        updated_participants = updated_response.json()["Tennis Club"]["participants"]
        for participant in original_participants:
            assert participant in updated_participants


class TestUnregisterFromActivity:
    """Test suite for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert "michael@mergington.edu" not in participants

    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_participant_not_signed_up(self, client, reset_activities):
        """Test unregistering a participant who is not signed up"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notstudent@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_preserves_other_participants(self, client, reset_activities):
        """Test that unregister preserves other participants"""
        original_response = client.get("/activities")
        original_participants = original_response.json()["Debate Team"]["participants"].copy()
        
        # Unregister one participant
        response = client.delete(
            "/activities/Debate Team/unregister?email=lucas@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify other participants are still there
        updated_response = client.get("/activities")
        updated_participants = updated_response.json()["Debate Team"]["participants"]
        
        assert "lucas@mergington.edu" not in updated_participants
        for participant in original_participants:
            if participant != "lucas@mergington.edu":
                assert participant in updated_participants

    def test_unregister_then_signup_same_participant(self, client, reset_activities):
        """Test unregistering and then signing up the same participant"""
        email = "michael@mergington.edu"
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/Chess Club/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Sign up again
        signup_response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant is back
        activities_response = client.get("/activities")
        participants = activities_response.json()["Chess Club"]["participants"]
        assert email in participants


class TestRootEndpoint:
    """Test suite for GET / endpoint"""

    def test_root_redirect(self, client, reset_activities):
        """Test that root endpoint redirects to static index"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
