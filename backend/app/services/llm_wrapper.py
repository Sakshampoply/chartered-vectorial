"""
LLM Client wrapper for OpenRouter API

Handles:
- API calls to OpenRouter
- Retry logic and error handling
- Token counting and cost tracking
- Async/await patterns
"""

from __future__ import annotations
import logging
import asyncio
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured LLM response"""
    text: str
    model: str
    usage_tokens: int
    stop_reason: str
    raw_response: Dict[str, Any]


class LLMClient:
    """
    Client for interacting with OpenRouter LLM API
    Handles retries, error recovery, and structured outputs
    """
    
    def __init__(self, config: LLMConfig):
        from app.agents.config import LLMConfig as LocalLLMConfig
        
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.api_base,
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://investment-advisory.local",
                "X-Title": "Investment Advisory Platform",
            }
        )
        self.retry_count = 0
    
    async def generate(
        self,
        prompt: str,
        use_case: str = "default",
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate text using LLM
        
        Args:
            prompt: User prompt
            use_case: Type of task (for optimization)
            system_prompt: Optional system context
            temperature: Override default temperature
            max_tokens: Override default max tokens
        
        Returns:
            LLMResponse: Structured response
        
        Raises:
            Exception: If all retries fail
        """
        temperature = temperature or self.config.get_temperature_for_use_case(use_case)
        max_tokens = max_tokens or self.config.max_tokens
        model = self.config.get_model_for_use_case(use_case)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": self.config.top_p,
            "max_tokens": max_tokens,
        }
        
        # Retry logic
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                return LLMResponse(
                    text=data["choices"][0]["message"]["content"],
                    model=data.get("model", model),
                    usage_tokens=data.get("usage", {}).get("total_tokens", 0),
                    stop_reason=data["choices"][0].get("finish_reason", "stop"),
                    raw_response=data,
                )
            
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                
                if e.response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code == 500:  # Server error
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise
                else:
                    raise
            
            except Exception as e:
                logger.error(f"Error calling LLM (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    raise
        
        raise Exception(f"Failed to get LLM response after {self.config.max_retries} attempts")
    
    async def structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        use_case: str = "default",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output matching schema
        
        Args:
            prompt: User prompt
            output_schema: JSON schema for output
            use_case: Type of task
            system_prompt: Optional system context
        
        Returns:
            Dict: Parsed JSON matching schema
        """
        schema_text = json.dumps(output_schema, indent=2)
        
        structured_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{schema_text}

Respond ONLY with the JSON object, no other text."""
        
        response = await self.generate(
            prompt=structured_prompt,
            use_case=use_case,
            system_prompt=system_prompt,
        )
        
        # Parse JSON response
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response.text}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class LLMWrapper:
    """
    Wrapper around LLMClient for backward compatibility and convenience.
    Provides a simpler interface for services that need LLM functionality.
    """
    
    def __init__(self, model_name: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        Initialize LLMWrapper
        
        Args:
            model_name: Optional model override (for backward compatibility)
            config: Optional LLMConfig (creates default if not provided)
        """
        if config is None:
            from app.agents.config import get_llm_config
            config = get_llm_config()
        
        # Override model if specified
        if model_name:
            config.model = model_name
        
        self.config = config
        self.client = LLMClient(config)
    
    async def agenerate_json(
        self,
        prompt: str,
        output_schema: Optional[Dict[str, Any]] = None,
        use_case: str = "default",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output
        
        Args:
            prompt: User prompt
            output_schema: Optional JSON schema (if not included in prompt)
            use_case: Type of task
            system_prompt: Optional system context
            
        Returns:
            Dict: Parsed JSON response
        """
        if output_schema:
            return await self.client.structured_output(
                prompt=prompt,
                output_schema=output_schema,
                use_case=use_case,
                system_prompt=system_prompt,
            )
        else:
            # Assume JSON is embedded in prompt
            response = await self.client.generate(
                prompt=prompt,
                use_case=use_case,
                system_prompt=system_prompt,
            )
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from response: {response.text}")
                raise
    
    async def generate(
        self,
        prompt: str,
        use_case: str = "default",
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text response
        
        Args:
            prompt: User prompt
            use_case: Type of task
            system_prompt: Optional system context
            temperature: Override temperature
            max_tokens: Override max tokens
            
        Returns:
            str: Generated text
        """
        response = await self.client.generate(
            prompt=prompt,
            use_case=use_case,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.text
    
    async def close(self):
        """Close the underlying client"""
        await self.client.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """
    Factory function to get LLM client
    
    Args:
        config: Optional LLMConfig (uses environment if not provided)
    
    Returns:
        LLMClient: Configured client
    """
    if not config:
        from app.agents.config import get_llm_config
        config = get_llm_config()
    
    return LLMClient(config)
