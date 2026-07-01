import pytest
from unittest.mock import patch
from src.modules.interviewEngine.flowController import process_answer_pipeline
from src.core.exceptions import PipelineError

@pytest.mark.asyncio
async def test_process_answer_pipeline_runs_agents_concurrently():
    with patch("src.agents.liveCoachAgent.liveCoachAgent") as mock_coach, \
         patch("src.agents.difficultyCalibratorAgent.difficultyCalibratorAgent") as mock_calibrator, \
         patch("src.agents.followUpAgent.followUpAgent") as mock_followup:
         
        mock_coach.return_value = {"coaching_feedback": [{"score_preview": 8}]}
        mock_calibrator.return_value = {"difficulty_level": 3}
        mock_followup.return_value = {"next_question": {"text": "followup?"}}
        
        state = {"test": "state"}
        result = await process_answer_pipeline(state)
        
        mock_coach.assert_called_once_with(state)
        mock_calibrator.assert_called_once_with(state)
        mock_followup.assert_called_once_with(state)
        
        assert result["coaching_feedback"] == [{"score_preview": 8}]
        assert result["difficulty_level"] == 3
        assert result["next_question"] == {"text": "followup?"}

@pytest.mark.asyncio
async def test_process_answer_pipeline_raises_on_agent_failure():
    with patch("src.agents.liveCoachAgent.liveCoachAgent") as mock_coach, \
         patch("src.agents.difficultyCalibratorAgent.difficultyCalibratorAgent") as mock_calibrator, \
         patch("src.agents.followUpAgent.followUpAgent") as mock_followup:
         
        mock_coach.side_effect = Exception("Coach failed")
        
        state = {}
        with pytest.raises(PipelineError) as exc_info:
            await process_answer_pipeline(state)
            
        assert exc_info.value.agentName == "live_coach_agent"
        assert "Coach failed" in str(exc_info.value.originalException)
