"""
Groq AI Service with Round-Robin API Key Rotation
Path: backend/app/services/groq_service.py

UPDATED: Added multiple API key support with automatic rotation
UNCHANGED: All prompts, methods, and business logic remain exactly the same
"""

import os
import httpx
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages multiple Groq API keys with round-robin rotation."""
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_index = 0
        self.key_cooldowns: Dict[str, datetime] = {}
        self.key_usage_count: Dict[str, int] = {key: 0 for key in api_keys}
        self.cooldown_duration = timedelta(minutes=1)
        
        logger.info(f"🔑 Initialized with {len(api_keys)} Groq API keys")
    
    def get_next_key(self) -> str:
        """Get next available API key (round-robin)."""
        attempts = 0
        
        while attempts < len(self.api_keys):
            key = self.api_keys[self.current_index]
            
            # Check if key is in cooldown
            if key in self.key_cooldowns and datetime.now() < self.key_cooldowns[key]:
                logger.debug(f"Key {self.current_index + 1} in cooldown, trying next...")
                self.current_index = (self.current_index + 1) % len(self.api_keys)
                attempts += 1
                continue
            
            # Remove expired cooldown
            if key in self.key_cooldowns:
                del self.key_cooldowns[key]
            
            return key
        
        # All keys in cooldown - return one with earliest expiry
        if self.key_cooldowns:
            earliest_key = min(self.key_cooldowns.items(), key=lambda x: x[1])[0]
            logger.warning("⚠️ All keys in cooldown! Using earliest expiry key.")
            return earliest_key
        
        return self.api_keys[self.current_index]
    
    def rotate(self):
        """Move to next key in rotation."""
        self.current_index = (self.current_index + 1) % len(self.api_keys)
    
    def mark_success(self, key: str):
        """Mark successful API call."""
        self.key_usage_count[key] = self.key_usage_count.get(key, 0) + 1
        if key in self.key_cooldowns:
            del self.key_cooldowns[key]
        self.rotate()
    
    def mark_rate_limited(self, key: str):
        """Mark key as rate-limited."""
        cooldown_until = datetime.now() + self.cooldown_duration
        self.key_cooldowns[key] = cooldown_until
        logger.warning(f"🚫 Key rate-limited. Cooldown until {cooldown_until.strftime('%H:%M:%S')}")
        self.rotate()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all keys."""
        return {
            "total_keys": len(self.api_keys),
            "current_key_index": self.current_index + 1,
            "keys_in_cooldown": len(self.key_cooldowns),
            "key_usage": self.key_usage_count,
            "active_cooldowns": {
                f"key_{self.api_keys.index(k) + 1}": expires.strftime('%H:%M:%S')
                for k, expires in self.key_cooldowns.items()
            }
        }
class GroqService:
    """Service to interact with Groq API using Llama 4 Scout model."""
    
    def __init__(self):
        # Initialize with multiple API keys
        self.api_keys = settings.groq_api_keys_list
        self.key_manager = APIKeyManager(self.api_keys)
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = settings.GROQ_MODEL
        
        logger.info(f"✅ Groq Service ready with {len(self.api_keys)} API keys")
    
    def _get_headers(self, api_key: str) -> Dict[str, str]:
        """Get request headers with API key."""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Make a chat completion request to Groq API with automatic key rotation."""
        
        # Clean messages before sending
        cleaned_messages = self._clean_messages_for_api(messages)
        
        payload = {
            "model": self.model,
            "messages": cleaned_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        # Try with automatic key rotation
        max_attempts = len(self.api_keys)
        
        for attempt in range(max_attempts):
            current_key = self.key_manager.get_next_key()
            headers = self._get_headers(current_key)
            
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    # Check for rate limit
                    if response.status_code == 429:
                        logger.warning(f"⚠️ Rate limit hit on key {attempt + 1}")
                        self.key_manager.mark_rate_limited(current_key)
                        continue
                    
                    response.raise_for_status()
                    
                    # Success!
                    self.key_manager.mark_success(current_key)
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited
                    self.key_manager.mark_rate_limited(current_key)
                    logger.warning(f"Rate limit on attempt {attempt + 1}, rotating key...")
                    continue
                else:
                    logger.error(f"HTTP error: {e.response.status_code}")
                    raise Exception(f"Groq API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Error calling Groq API: {str(e)}")
                raise
        
        # All keys failed
        raise Exception("All API keys are rate-limited. Please try again in 1 minute.")
    
    def _clean_messages_for_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Clean messages for API by removing non-serializable fields like datetime.
        Only keep 'role' and 'content' fields.
        """
        cleaned = []
        for msg in messages:
            cleaned_msg = {
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            }
            cleaned.append(cleaned_msg)
        return cleaned
    
    # ==========================================
    # ALL METHODS BELOW REMAIN EXACTLY THE SAME
    # Only the internal API calls use key rotation
    # ==========================================
    
    async def generate_roadmap_outline(
        self,
        career_path: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        STEP 1: Generate ONLY 4 phase outlines (Fast - 2-3 seconds).
        No detailed weeks/resources yet.
        """
        
        current_skills = user_profile.get("profile_data", {}).get("technical_skills", "")
        education = user_profile.get("profile_data", {}).get("branch", "")
        experience = user_profile.get("profile_data", {}).get("experience", "")
        
        prompt = f"""You are an expert career coach. Generate a 4-phase learning roadmap outline.

**Target Career:** {career_path}
**User's Skills:** {current_skills}
**Education:** {education}
**Experience:** {experience}

**Requirements:**
1. Create EXACTLY 4 phases
2. Each phase has 4 weeks (total 16 weeks)
3. Phases: Foundation → Intermediate → Advanced → Expert
4. For each phase provide ONLY:
   - Phase title
   - Brief description (2-3 sentences)
   - Difficulty level
   - Prerequisites
   - Learning outcomes (3-5 items)

DO NOT generate weekly schedules or resources yet.

**Output JSON:**
{{
  "roadmap_title": "{career_path} Learning Path",
  "description": "Complete roadmap to become {career_path}",
  "total_weeks": 16,
  "phases": [
    {{
      "phase_number": 1,
      "title": "Foundation Phase",
      "description": "Build fundamental skills...",
      "difficulty": "beginner",
      "duration_weeks": 4,
      "prerequisites": [],
      "learning_outcomes": ["outcome1", "outcome2", "outcome3"],
      "is_unlocked": true,
      "is_generated": false
    }},
    {{
      "phase_number": 2,
      "title": "Intermediate Phase",
      "description": "...",
      "difficulty": "intermediate",
      "duration_weeks": 4,
      "prerequisites": ["Complete Foundation Phase"],
      "learning_outcomes": ["...", "..."],
      "is_unlocked": false,
      "is_generated": false
    }},
    {{
      "phase_number": 3,
      "title": "Advanced Phase",
      "description": "...",
      "difficulty": "advanced",
      "duration_weeks": 4,
      "prerequisites": ["Complete Intermediate Phase"],
      "learning_outcomes": ["...", "..."],
      "is_unlocked": false,
      "is_generated": false
    }},
    {{
      "phase_number": 4,
      "title": "Expert Phase",
      "description": "...",
      "difficulty": "expert",
      "duration_weeks": 4,
      "prerequisites": ["Complete Advanced Phase"],
      "learning_outcomes": ["...", "..."],
      "is_unlocked": false,
      "is_generated": false
    }}
  ]
}}

Generate now. Only JSON, no other text."""

        messages = [
            {"role": "system", "content": "You are a career coach. Respond ONLY with valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.chat_completion(messages=messages, temperature=0.7, max_tokens=2000)
            content = response["choices"][0]["message"]["content"]
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            roadmap_data = json.loads(content)
            logger.info(f"Generated roadmap outline for {career_path}")
            return roadmap_data
        
        except Exception as e:
            logger.error(f"Error generating outline: {str(e)}")
            raise


    async def generate_phase_details(
        self,
        career_path: str,
        phase_number: int,
        phase_info: Dict[str, Any],
        user_profile: Dict[str, Any],
        time_per_week: int = 10
    ) -> List[Dict[str, Any]]:
        """
        STEP 2: Generate detailed content for ONE phase (4 weeks).
        Called when user clicks to unlock a phase.
        Returns 4 weeks of detailed content with resources.
        """
        
        current_skills = user_profile.get("profile_data", {}).get("technical_skills", "")
        phase_title = phase_info.get("title", f"Phase {phase_number}")
        phase_description = phase_info.get("description", "")
        
        prompt = f"""Generate detailed 4-week curriculum for Phase {phase_number}: {phase_title}

**Context:**
- Career: {career_path}
- Phase: {phase_title}
- Description: {phase_description}
- User's Skills: {current_skills}
- Time Available: {time_per_week} hours/week

**Requirements:**
Generate EXACTLY 4 weeks of content. Each week must have:

1. Week title and description
2. 3-5 specific topics to learn
3. 5-7 learning resources with:
   - Title
   - Type (video/article/documentation/tutorial)
   - Real URL (YouTube, MDN, freeCodeCamp, W3Schools, etc.)
   - Description
   - Duration/length
   - Source name
   - is_free: true/false

4. 2-3 practical exercises/projects
5. Estimated hours needed
6. Learning outcomes (what they'll achieve)

**Output JSON (array of 4 weeks):**
[
  {{
    "week_number": 1,
    "title": "Introduction to...",
    "description": "Learn the basics of...",
    "topics": ["Topic 1", "Topic 2", "Topic 3"],
    "resources": [
      {{
        "title": "HTML Crash Course",
        "type": "video",
        "url": "https://youtube.com/watch?v=...",
        "description": "Complete HTML tutorial",
        "duration": "2 hours",
        "source": "Traversy Media",
        "is_free": true
      }},
      {{
        "title": "MDN HTML Guide",
        "type": "documentation",
        "url": "https://developer.mozilla.org/en-US/docs/Web/HTML",
        "description": "Official HTML docs",
        "duration": "Reading material",
        "source": "MDN Web Docs",
        "is_free": true
      }}
    ],
    "exercises": [
      "Build a personal portfolio page",
      "Create a responsive navigation menu"
    ],
    "estimated_hours": {time_per_week},
    "learning_outcomes": [
      "Understand HTML structure",
      "Create semantic markup"
    ]
  }},
  {{
    "week_number": 2,
    "title": "...",
    "description": "...",
    "topics": ["...", "..."],
    "resources": [...],
    "exercises": [...],
    "estimated_hours": {time_per_week},
    "learning_outcomes": [...]
  }},
  {{
    "week_number": 3,
    ...
  }},
  {{
    "week_number": 4,
    ...
  }}
]

IMPORTANT: Use real, working URLs from popular learning platforms. Generate all 4 weeks now."""

        messages = [
            {"role": "system", "content": "You are a curriculum designer. Respond ONLY with valid JSON array."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self.chat_completion(messages=messages, temperature=0.7, max_tokens=4000)
            content = response["choices"][0]["message"]["content"]
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            weekly_schedule = json.loads(content)
            
            # Validate we got 4 weeks
            if not isinstance(weekly_schedule, list) or len(weekly_schedule) != 4:
                raise ValueError(f"Expected 4 weeks, got {len(weekly_schedule) if isinstance(weekly_schedule, list) else 'invalid'}")
            
            logger.info(f"Generated Phase {phase_number} details with {len(weekly_schedule)} weeks")
            return weekly_schedule
        
        except Exception as e:
            logger.error(f"Error generating phase details: {str(e)}")
            raise


    async def career_coach_chat_stream(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        chat_history: List[Dict[str, str]] = None,
        roadmap_context: Optional[Dict[str, Any]] = None
    ):
        """AI career coach conversation with streaming response."""
        
        # Build personalized context
        profile_data = user_profile.get('profile_data', {})
        skills = profile_data.get('technical_skills', [])
        skills_str = ', '.join(skills) if isinstance(skills, list) else str(skills) if skills else 'Not specified'
        
        profile_summary = f"""User Profile:
- Name: {user_profile.get('full_name', 'Student')}
- Skills: {skills_str}
- Education: {profile_data.get('college_name', 'Not specified')}
- Career Goals: {profile_data.get('preferred_roles', 'Exploring options')}"""
        
        roadmap_info = ""
        if roadmap_context:
            roadmap_info = f"""
Current Learning Journey:
- Career Path: {roadmap_context.get('career_path', 'N/A')}
- Progress: {roadmap_context.get('progress_percentage', 0)}%
- Current Phase: {roadmap_context.get('current_phase', 1)} (Week {roadmap_context.get('current_week', 1)})"""
        
        system_prompt = f"""You are an AI career advisor helping students with their job search and career development.

{profile_summary}
{roadmap_info}

RESPONSE GUIDELINES:
1. Keep responses SHORT (3-5 sentences OR bullet points)
2. Use bullet points (•) for lists - NEVER use ** or ## markdown
3. Be direct, friendly, and actionable
4. Only provide detailed explanations if explicitly asked
5. Stay within your role as a career advisor

FORMATTING RULES:
✓ Good: "Here are key points:
- Skill 1
- Skill 2
That's a good start!"

✗ Bad: Long paragraphs, **bold text**, ### headings

SCOPE:
- Answer questions about: careers, skills, learning paths, job search, resume, interview prep
- Politely decline: homework help, technical debugging, personal advice unrelated to career

If asked something outside career guidance, respond: "I'm focused on career guidance. Let's talk about your professional goals instead!"

Keep responses under 100 words unless asked to "explain in detail"."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history (last 10 messages) - cleaned
        if chat_history:
            for msg in chat_history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        messages.append({"role": "user", "content": user_message})
        
        # Clean messages before sending
        cleaned_messages = self._clean_messages_for_api(messages)
        
        payload = {
            "model": self.model,
            "messages": cleaned_messages,
            "temperature": 0.6,
            "max_tokens": 400,
            "stream": True,
            "top_p": 0.9
        }
        
        # Try with key rotation for streaming
        max_attempts = len(self.api_keys)
        
        for attempt in range(max_attempts):
            current_key = self.key_manager.get_next_key()
            headers = self._get_headers(current_key)
            
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    ) as response:
                        # Check for rate limit
                        if response.status_code == 429:
                            logger.warning(f"⚠️ Streaming rate limit on key {attempt + 1}")
                            self.key_manager.mark_rate_limited(current_key)
                            continue
                        
                        response.raise_for_status()
                        
                        # Success! Stream the response
                        self.key_manager.mark_success(current_key)
                        
                        async for line in response.aiter_lines():
                            if line.strip() and line.startswith("data: "):
                                data = line[6:]
                                
                                if data.strip() == "[DONE]":
                                    break
                                
                                try:
                                    chunk = json.loads(data)
                                    if chunk.get("choices") and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                        return  # Successfully completed streaming
                                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    self.key_manager.mark_rate_limited(current_key)
                    continue
                else:
                    logger.error(f"Error in career coach streaming: {str(e)}")
                    yield "Hey, I'm having a bit of trouble connecting right now. Mind giving it another shot in a moment? 🤔"
                    return
            except Exception as e:
                logger.error(f"Error in career coach streaming: {str(e)}")
                yield "Hey, I'm having a bit of trouble connecting right now. Mind giving it another shot in a moment? 🤔"
                return
        
        # All keys failed
        yield "All API keys are currently rate-limited. Please try again in a minute. 🕐"


# Singleton instance - lazy initialization
_groq_service_instance = None

def get_groq_service() -> GroqService:
    """Get or create the Groq service singleton instance."""
    global _groq_service_instance
    if _groq_service_instance is None:
        _groq_service_instance = GroqService()
    return _groq_service_instance


# For backward compatibility - create instance on first access
class _GroqServiceProxy:
    def __getattr__(self, name):
        return getattr(get_groq_service(), name)

groq_service = _GroqServiceProxy()