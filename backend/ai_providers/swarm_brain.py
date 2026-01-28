"""
SWARM BRAIN - Multi-AI Orchestrator for Comic Grading & Research
=================================================================
Coordinates multiple AI providers for optimal task distribution:

VISION SWARM (Grading):
- Claude (Anthropic) - Primary grader, highest accuracy
- Gemini (Google) - Secondary grader, good metadata extraction
- OpenRouter (Qwen VL 72B, Llama Vision, Gemma) - Free vision models
- Grok (xAI) - Fast vision grading
- Groq (Llama Vision) - Ultra-fast inference
- Ollama (Local) - Backup/offline grading

RESEARCH SWARM (Data Retrieval):
- Perplexity - Web search, pricing research, comic history
- Cohere - Document analysis, semantic search
- DeepSeek - Text analysis, metadata extraction
- OpenRouter Text Models - Free research models

DATA SWARM (Scraping/APIs):
- eBay Scraper - Sold listings, current listings, price trends
- CGC Census - Population reports
- GPA/GoCollect - Price history
- Heritage Auctions - Auction results
- Comic Vine - Metadata database

Architecture: Each swarm operates in parallel, results are merged by consensus.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks the swarm can handle"""
    GRADE_COMIC = "grade_comic"           # Vision - grade comic condition
    IDENTIFY_COMIC = "identify_comic"     # Vision - identify title/issue
    RESEARCH_PRICING = "research_pricing" # Research - find market prices
    RESEARCH_HISTORY = "research_history" # Research - comic history/significance
    SCRAPE_EBAY = "scrape_ebay"          # Data - eBay sold/listed
    FETCH_CENSUS = "fetch_census"        # Data - CGC population
    FETCH_METADATA = "fetch_metadata"    # Data - Comic Vine, GCD


class AIRole(Enum):
    """Role of each AI in the swarm"""
    VISION_PRIMARY = "vision_primary"       # Main grading (Claude, Gemini)
    VISION_SECONDARY = "vision_secondary"   # Backup grading (OpenRouter, Grok)
    VISION_FAST = "vision_fast"             # Quick grading (Groq)
    VISION_LOCAL = "vision_local"           # Offline grading (Ollama)
    RESEARCH_WEB = "research_web"           # Web research (Perplexity)
    RESEARCH_SEMANTIC = "research_semantic" # Semantic analysis (Cohere)
    RESEARCH_TEXT = "research_text"         # Text analysis (DeepSeek)
    DATA_SCRAPER = "data_scraper"          # Data fetching (scrapers)


@dataclass
class SwarmMember:
    """Configuration for a swarm AI member"""
    name: str
    provider: str
    role: AIRole
    tasks: List[TaskType]
    weight: float = 1.0
    enabled: bool = True
    timeout_seconds: int = 60
    cost_per_call: float = 0.0  # For tracking API costs
    priority: int = 1  # Lower = higher priority


@dataclass
class SwarmResult:
    """Result from a swarm member"""
    member_name: str
    task_type: TaskType
    success: bool
    data: Dict[str, Any]
    confidence: float = 0.0
    latency_ms: int = 0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SwarmBrain:
    """
    Orchestrates multiple AI providers for comic grading and research.
    Uses parallel execution with intelligent task routing.
    """

    def __init__(self):
        self.members: Dict[str, SwarmMember] = {}
        self.results_cache: Dict[str, SwarmResult] = {}
        self._setup_swarm()

    def _setup_swarm(self):
        """Initialize all swarm members"""

        # ===== VISION SWARM (Grading) =====
        self.members['claude'] = SwarmMember(
            name='claude',
            provider='Anthropic',
            role=AIRole.VISION_PRIMARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.35,
            priority=1,
            cost_per_call=0.003  # ~$0.003 per image
        )

        self.members['gemini'] = SwarmMember(
            name='gemini',
            provider='Google',
            role=AIRole.VISION_PRIMARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.25,
            priority=1,
            cost_per_call=0.0  # Free tier
        )

        self.members['openrouter_qwen'] = SwarmMember(
            name='openrouter_qwen',
            provider='OpenRouter',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.15,
            priority=2,
            cost_per_call=0.0  # Free model
        )

        self.members['openrouter_llama'] = SwarmMember(
            name='openrouter_llama',
            provider='OpenRouter',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.10,
            priority=2,
            cost_per_call=0.0  # Free model
        )

        self.members['grok'] = SwarmMember(
            name='grok',
            provider='xAI',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.10,
            priority=2,
            timeout_seconds=30
        )

        self.members['groq'] = SwarmMember(
            name='groq',
            provider='Groq',
            role=AIRole.VISION_FAST,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.05,
            priority=3,
            timeout_seconds=15  # Ultra-fast
        )

        self.members['ollama'] = SwarmMember(
            name='ollama',
            provider='Ollama',
            role=AIRole.VISION_LOCAL,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.05,
            priority=4,
            timeout_seconds=120,  # Local can be slow
            cost_per_call=0.0
        )

        # ===== NEW FREE VISION MODELS (OpenRouter) =====
        self.members['openrouter_llama4_maverick'] = SwarmMember(
            name='openrouter_llama4_maverick',
            provider='OpenRouter',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.12,
            priority=2,
            cost_per_call=0.0  # Free model - Llama 4 Maverick 400B MoE
        )

        self.members['openrouter_mistral_small'] = SwarmMember(
            name='openrouter_mistral_small',
            provider='OpenRouter',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.10,
            priority=2,
            cost_per_call=0.0  # Free model - Mistral Small 3.1 24B
        )

        self.members['openrouter_gemma3'] = SwarmMember(
            name='openrouter_gemma3',
            provider='OpenRouter',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.08,
            priority=2,
            cost_per_call=0.0  # Free model - Gemma 3 27B
        )

        self.members['openrouter_kimi'] = SwarmMember(
            name='openrouter_kimi',
            provider='OpenRouter',
            role=AIRole.VISION_FAST,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.05,
            priority=3,
            timeout_seconds=30,
            cost_per_call=0.0  # Free model - Kimi-VL
        )

        self.members['openrouter_llama4_scout'] = SwarmMember(
            name='openrouter_llama4_scout',
            provider='OpenRouter',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.08,
            priority=2,
            cost_per_call=0.0  # Free model - Llama 4 Scout 10M context
        )

        # ===== CLOUDFLARE WORKERS AI =====
        self.members['cloudflare'] = SwarmMember(
            name='cloudflare',
            provider='Cloudflare',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.08,
            priority=3,
            timeout_seconds=60,
            cost_per_call=0.0  # Free tier - 10K neurons/day
        )

        # ===== HUGGINGFACE INFERENCE =====
        self.members['huggingface'] = SwarmMember(
            name='huggingface',
            provider='HuggingFace',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.06,
            priority=3,
            timeout_seconds=120,  # Models may need to warm up
            cost_per_call=0.0  # Free tier
        )

        # ===== TOGETHER AI FREE =====
        self.members['together'] = SwarmMember(
            name='together',
            provider='Together',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.10,
            priority=2,
            timeout_seconds=60,
            cost_per_call=0.0  # Free Llama Vision endpoint
        )

        # ===== HYPERBOLIC FREE =====
        self.members['hyperbolic'] = SwarmMember(
            name='hyperbolic',
            provider='Hyperbolic',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.10,
            priority=2,
            timeout_seconds=60,
            cost_per_call=0.0  # Free 60 req/min
        )

        # ===== SAMBANOVA FREE =====
        self.members['sambanova'] = SwarmMember(
            name='sambanova',
            provider='SambaNova',
            role=AIRole.VISION_SECONDARY,
            tasks=[TaskType.GRADE_COMIC, TaskType.IDENTIFY_COMIC],
            weight=0.10,
            priority=2,
            timeout_seconds=60,
            cost_per_call=0.0  # Free Llama 4 Maverick
        )

        # ===== RESEARCH SWARM (Data Retrieval) =====
        self.members['perplexity'] = SwarmMember(
            name='perplexity',
            provider='Perplexity',
            role=AIRole.RESEARCH_WEB,
            tasks=[TaskType.RESEARCH_PRICING, TaskType.RESEARCH_HISTORY, TaskType.FETCH_METADATA],
            weight=0.40,
            priority=1,
            timeout_seconds=30
        )

        self.members['cohere'] = SwarmMember(
            name='cohere',
            provider='Cohere',
            role=AIRole.RESEARCH_SEMANTIC,
            tasks=[TaskType.RESEARCH_HISTORY, TaskType.FETCH_METADATA],
            weight=0.30,
            priority=2,
            timeout_seconds=30
        )

        self.members['deepseek_research'] = SwarmMember(
            name='deepseek_research',
            provider='DeepSeek',
            role=AIRole.RESEARCH_TEXT,
            tasks=[TaskType.RESEARCH_HISTORY, TaskType.FETCH_METADATA],
            weight=0.30,
            priority=2,
            timeout_seconds=30
        )

        # ===== DATA SWARM (Scrapers) =====
        self.members['ebay_scraper'] = SwarmMember(
            name='ebay_scraper',
            provider='eBay',
            role=AIRole.DATA_SCRAPER,
            tasks=[TaskType.SCRAPE_EBAY, TaskType.RESEARCH_PRICING],
            weight=0.35,
            priority=1,
            timeout_seconds=60
        )

        self.members['cgc_census'] = SwarmMember(
            name='cgc_census',
            provider='CGC',
            role=AIRole.DATA_SCRAPER,
            tasks=[TaskType.FETCH_CENSUS],
            weight=0.30,
            priority=1,
            timeout_seconds=30
        )

        self.members['gpa_scraper'] = SwarmMember(
            name='gpa_scraper',
            provider='GPA/GoCollect',
            role=AIRole.DATA_SCRAPER,
            tasks=[TaskType.RESEARCH_PRICING],
            weight=0.35,
            priority=1,
            timeout_seconds=30
        )

        logger.info(f"SwarmBrain initialized with {len(self.members)} members")

    def get_members_for_task(self, task_type: TaskType, enabled_only: bool = True) -> List[SwarmMember]:
        """Get all members capable of handling a task"""
        members = [
            m for m in self.members.values()
            if task_type in m.tasks and (not enabled_only or m.enabled)
        ]
        # Sort by priority (lower = higher priority)
        return sorted(members, key=lambda m: (m.priority, -m.weight))

    async def grade_comic(
        self,
        image_base64: str,
        metadata: Optional[Dict] = None,
        use_all_providers: bool = False,
        min_providers: int = 2
    ) -> Dict[str, Any]:
        """
        Grade a comic using the vision swarm.

        Args:
            image_base64: Base64-encoded comic image
            metadata: Optional known metadata
            use_all_providers: Use all available providers (slower, more accurate)
            min_providers: Minimum providers for consensus

        Returns:
            Consensus grading result with individual grades
        """
        start_time = datetime.utcnow()

        # Get vision members
        vision_members = self.get_members_for_task(TaskType.GRADE_COMIC)

        if not use_all_providers:
            # Use only primary and secondary (faster)
            vision_members = [m for m in vision_members if m.role in [
                AIRole.VISION_PRIMARY, AIRole.VISION_SECONDARY
            ]][:4]  # Max 4 providers for speed

        logger.info(f"[SWARM] Grading with {len(vision_members)} providers: {[m.name for m in vision_members]}")

        # Run grading tasks in parallel
        tasks = []
        for member in vision_members:
            task = self._run_grading_task(member, image_base64, metadata)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        valid_results = []
        ai_grades = {}

        for i, result in enumerate(results):
            member = vision_members[i]
            if isinstance(result, SwarmResult) and result.success:
                valid_results.append(result)
                ai_grades[member.name] = {
                    'grade': result.data.get('grade', 0),
                    'confidence': result.confidence,
                    'provider': member.provider,
                    'weight': member.weight,
                    'latency_ms': result.latency_ms,
                    'comic_info': result.data.get('comic_info', {}),
                    'key_issue_info': result.data.get('key_issue_info', {}),
                    'defects': result.data.get('defects', []),
                    'reasoning': result.data.get('reasoning', '')
                }
            elif isinstance(result, Exception):
                logger.error(f"[SWARM] {member.name} failed: {result}")
                ai_grades[member.name] = {'error': str(result), 'grade': 0}

        if len(valid_results) < min_providers:
            logger.warning(f"[SWARM] Only {len(valid_results)} valid results, need {min_providers}")

        # Calculate consensus
        consensus = self._calculate_consensus(valid_results)

        # Merge comic_info from all providers
        merged_comic_info = self._merge_comic_info([r.data for r in valid_results])

        # Merge key_issue_info
        merged_key_info = self._merge_key_issue_info([r.data for r in valid_results])

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return {
            'consensus_grade': consensus['grade'],
            'grade_label': consensus['label'],
            'confidence': consensus['confidence'],
            'agreement_percentage': consensus['agreement'],
            'ai_grades': ai_grades,
            'comic_info': merged_comic_info,
            'key_issue_info': merged_key_info,
            'confirmed_defects': consensus['defects'],
            'provider_count': len(valid_results),
            'total_latency_ms': elapsed_ms,
            'swarm_mode': 'full' if use_all_providers else 'fast'
        }

    async def research_comic(
        self,
        title: str,
        issue_number: str,
        publisher: Optional[str] = None,
        year: Optional[str] = None,
        grade: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Research a comic using the research swarm.
        Fetches pricing, history, significance, and metadata.
        """
        start_time = datetime.utcnow()

        # Prepare research query
        query = f"{title} #{issue_number}"
        if publisher:
            query += f" {publisher}"
        if year:
            query += f" {year}"

        # Get research members
        research_members = self.get_members_for_task(TaskType.RESEARCH_PRICING)
        data_members = self.get_members_for_task(TaskType.SCRAPE_EBAY)

        logger.info(f"[SWARM] Researching '{query}' with {len(research_members)} research + {len(data_members)} data providers")

        # Run all research tasks in parallel
        tasks = []

        # Perplexity - pricing and history
        if 'perplexity' in self.members and self.members['perplexity'].enabled:
            tasks.append(self._run_perplexity_research(title, issue_number, publisher, grade))

        # Cohere - semantic analysis
        if 'cohere' in self.members and self.members['cohere'].enabled:
            tasks.append(self._run_cohere_research(title, issue_number, publisher))

        # eBay scraping - sold and listed
        if 'ebay_scraper' in self.members and self.members['ebay_scraper'].enabled:
            tasks.append(self._run_ebay_scrape(title, issue_number, grade))

        # CGC census
        if 'cgc_census' in self.members and self.members['cgc_census'].enabled:
            tasks.append(self._run_cgc_census(title, issue_number))

        # GPA/GoCollect pricing
        if 'gpa_scraper' in self.members and self.members['gpa_scraper'].enabled:
            tasks.append(self._run_gpa_lookup(title, issue_number, grade))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge all research results
        merged_data = {
            'pricing': {},
            'history': {},
            'census': {},
            'ebay_sold': [],
            'ebay_listed': [],
            'metadata': {},
            'sources': []
        }

        for result in results:
            if isinstance(result, dict):
                if 'pricing' in result:
                    merged_data['pricing'].update(result['pricing'])
                if 'history' in result:
                    merged_data['history'].update(result['history'])
                if 'census' in result:
                    merged_data['census'].update(result['census'])
                if 'ebay_sold' in result:
                    merged_data['ebay_sold'].extend(result['ebay_sold'])
                if 'ebay_listed' in result:
                    merged_data['ebay_listed'].extend(result['ebay_listed'])
                if 'metadata' in result:
                    merged_data['metadata'].update(result['metadata'])
                if 'source' in result:
                    merged_data['sources'].append(result['source'])

        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        merged_data['research_latency_ms'] = elapsed_ms

        return merged_data

    async def full_comic_analysis(
        self,
        image_base64: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Complete comic analysis: grade + research in parallel.
        This is the main entry point for full swarm operation.
        """
        start_time = datetime.utcnow()

        # Step 1: Grade the comic (get title/issue from vision)
        grading_result = await self.grade_comic(image_base64, metadata, use_all_providers=True)

        # Extract identified comic info
        comic_info = grading_result.get('comic_info', {})
        title = comic_info.get('title') or (metadata or {}).get('title', 'Unknown')
        issue = comic_info.get('issue_number') or (metadata or {}).get('issue', 'Unknown')
        publisher = comic_info.get('publisher')
        year = comic_info.get('year')
        grade = grading_result.get('consensus_grade')

        # Step 2: Research the comic (pricing, history, etc.)
        if title != 'Unknown' and issue != 'Unknown':
            research_result = await self.research_comic(title, issue, publisher, year, grade)
        else:
            research_result = {'error': 'Could not identify comic for research'}

        # Combine results
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return {
            'grading': grading_result,
            'research': research_result,
            'total_analysis_ms': elapsed_ms,
            'swarm_version': '1.0.0'
        }

    # ===== PRIVATE TASK RUNNERS =====

    async def _run_grading_task(
        self,
        member: SwarmMember,
        image_base64: str,
        metadata: Optional[Dict]
    ) -> SwarmResult:
        """Run a grading task for a specific member"""
        start_time = datetime.utcnow()

        try:
            # Import the appropriate grader
            if member.name == 'claude':
                from ai_providers.claude_grader import grade_with_claude
                result = await asyncio.wait_for(
                    grade_with_claude(image_base64, metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'gemini':
                from ai_providers.gemini_grader import grade_with_gemini
                result = await asyncio.wait_for(
                    grade_with_gemini(image_base64, metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'openrouter_qwen':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "qwen/qwen2.5-vl-72b-instruct:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'openrouter_llama':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "meta-llama/llama-3.2-11b-vision-instruct:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'grok':
                from ai_providers.grok_grader import grade_with_grok
                result = await asyncio.wait_for(
                    grade_with_grok(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'groq':
                from ai_providers.groq_grader import grade_with_groq
                result = await asyncio.wait_for(
                    grade_with_groq(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'ollama':
                from ai_providers.ollama_vision_grader import grade_with_ollama_vision
                result = await asyncio.wait_for(
                    grade_with_ollama_vision(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            # ===== NEW FREE VISION MODELS =====
            elif member.name == 'openrouter_llama4_maverick':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "meta-llama/llama-4-maverick:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'openrouter_mistral_small':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "mistralai/mistral-small-3.1-24b-instruct:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'openrouter_gemma3':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "google/gemma-3-27b-it:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'openrouter_kimi':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "moonshotai/kimi-vl-a3b-thinking:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'openrouter_llama4_scout':
                from ai_providers.openrouter_grader import grade_with_openrouter
                result = await asyncio.wait_for(
                    grade_with_openrouter(image_base64, "meta-llama/llama-4-scout:free", metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'cloudflare':
                from ai_providers.cloudflare_grader import grade_with_cloudflare
                result = await asyncio.wait_for(
                    grade_with_cloudflare(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'huggingface':
                from ai_providers.huggingface_grader import grade_with_huggingface
                result = await asyncio.wait_for(
                    grade_with_huggingface(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'together':
                from ai_providers.together_grader import grade_with_together
                result = await asyncio.wait_for(
                    grade_with_together(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'hyperbolic':
                from ai_providers.hyperbolic_grader import grade_with_hyperbolic
                result = await asyncio.wait_for(
                    grade_with_hyperbolic(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            elif member.name == 'sambanova':
                from ai_providers.sambanova_grader import grade_with_sambanova
                result = await asyncio.wait_for(
                    grade_with_sambanova(image_base64, metadata=metadata),
                    timeout=member.timeout_seconds
                )
            else:
                raise ValueError(f"Unknown grader: {member.name}")

            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            if result.get('error'):
                return SwarmResult(
                    member_name=member.name,
                    task_type=TaskType.GRADE_COMIC,
                    success=False,
                    data=result,
                    error=result['error'],
                    latency_ms=latency_ms
                )

            return SwarmResult(
                member_name=member.name,
                task_type=TaskType.GRADE_COMIC,
                success=True,
                data=result,
                confidence=result.get('confidence', 0.7),
                latency_ms=latency_ms
            )

        except asyncio.TimeoutError:
            return SwarmResult(
                member_name=member.name,
                task_type=TaskType.GRADE_COMIC,
                success=False,
                data={},
                error=f"Timeout after {member.timeout_seconds}s",
                latency_ms=member.timeout_seconds * 1000
            )
        except Exception as e:
            logger.error(f"[SWARM] {member.name} grading error: {e}")
            return SwarmResult(
                member_name=member.name,
                task_type=TaskType.GRADE_COMIC,
                success=False,
                data={},
                error=str(e),
                latency_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )

    async def _run_perplexity_research(
        self,
        title: str,
        issue: str,
        publisher: Optional[str],
        grade: Optional[float]
    ) -> Dict[str, Any]:
        """Run Perplexity web research"""
        try:
            from ai_providers.perplexity_research import full_comic_research
            # full_comic_research(title, issue_number, grade, publisher, year)
            result = await full_comic_research(
                title=title,
                issue_number=issue,
                grade=grade or 8.0,  # Default grade for pricing research
                publisher=publisher
            )
            result['source'] = 'perplexity'
            return result
        except Exception as e:
            logger.error(f"[SWARM] Perplexity research error: {e}")
            return {'error': str(e), 'source': 'perplexity'}

    async def _run_cohere_research(
        self,
        title: str,
        issue: str,
        publisher: Optional[str]
    ) -> Dict[str, Any]:
        """Run Cohere semantic research"""
        try:
            # Import or create Cohere research module
            from ai_providers.cohere_research import research_comic_history
            result = await research_comic_history(title, issue, publisher)
            result['source'] = 'cohere'
            return result
        except ImportError:
            # Cohere module not yet created
            return {'error': 'Cohere module not available', 'source': 'cohere'}
        except Exception as e:
            logger.error(f"[SWARM] Cohere research error: {e}")
            return {'error': str(e), 'source': 'cohere'}

    async def _run_ebay_scrape(
        self,
        title: str,
        issue: str,
        grade: Optional[float]
    ) -> Dict[str, Any]:
        """Run eBay scraping for sold and listed items"""
        try:
            from pricing_sources.ebay_scraper import search_ebay_sold, search_ebay_listings

            # Build search query
            query = f"{title} #{issue}"
            if grade:
                query += f" CGC {grade}"

            # Run both searches in parallel
            sold_task = search_ebay_sold(query)
            listed_task = search_ebay_listings(query)

            sold, listed = await asyncio.gather(sold_task, listed_task, return_exceptions=True)

            return {
                'ebay_sold': sold if isinstance(sold, list) else [],
                'ebay_listed': listed if isinstance(listed, list) else [],
                'source': 'ebay'
            }
        except Exception as e:
            logger.error(f"[SWARM] eBay scrape error: {e}")
            return {'error': str(e), 'source': 'ebay'}

    async def _run_cgc_census(
        self,
        title: str,
        issue: str
    ) -> Dict[str, Any]:
        """Run CGC census lookup"""
        try:
            from pricing_sources.cgc_lookup import fetch_cgc_data
            result = await fetch_cgc_data(title, issue)
            return {'census': result, 'source': 'cgc_census'}
        except Exception as e:
            logger.error(f"[SWARM] CGC census error: {e}")
            return {'error': str(e), 'source': 'cgc_census'}

    async def _run_gpa_lookup(
        self,
        title: str,
        issue: str,
        grade: Optional[float]
    ) -> Dict[str, Any]:
        """Run GPA/GoCollect price lookup"""
        try:
            from pricing_sources.gpa_scraper import fetch_gpa_price
            result = await fetch_gpa_price(title, issue, grade or 9.4)
            return {'pricing': result, 'source': 'gpa'}
        except Exception as e:
            logger.error(f"[SWARM] GPA lookup error: {e}")
            return {'error': str(e), 'source': 'gpa'}

    # ===== CONSENSUS HELPERS =====

    def _calculate_consensus(self, results: List[SwarmResult]) -> Dict[str, Any]:
        """Calculate weighted consensus from grading results"""
        if not results:
            return {'grade': 0, 'label': 'Error', 'confidence': 0, 'agreement': 0, 'defects': []}

        # Weighted average grade
        total_weight = 0
        weighted_sum = 0
        grades = []

        for result in results:
            member = self.members.get(result.member_name)
            weight = member.weight if member else 1.0
            grade = result.data.get('grade', 0)

            if grade > 0:
                weighted_sum += grade * weight
                total_weight += weight
                grades.append(grade)

        if total_weight == 0:
            return {'grade': 0, 'label': 'Error', 'confidence': 0, 'agreement': 0, 'defects': []}

        avg_grade = weighted_sum / total_weight
        min_grade = min(grades)

        # Favor stricter grades slightly
        consensus_grade = round(((avg_grade * 0.7) + (min_grade * 0.3)) * 2) / 2

        # Calculate agreement (how close are the grades)
        if len(grades) > 1:
            variance = sum((g - avg_grade) ** 2 for g in grades) / len(grades)
            std_dev = variance ** 0.5
            agreement = max(0, min(100, int((1 - std_dev / 3) * 100)))
        else:
            agreement = 100

        # Get grade label
        from ai_providers.claude_grader import get_grade_label
        label = get_grade_label(consensus_grade)

        # Collect confirmed defects (mentioned by 2+ providers)
        defect_counts = {}
        for result in results:
            for defect in result.data.get('defects', []):
                key = (defect.get('type', ''), defect.get('location', ''))
                if key not in defect_counts:
                    defect_counts[key] = {'defect': defect, 'count': 0}
                defect_counts[key]['count'] += 1

        confirmed_defects = [
            d['defect'] for d in defect_counts.values()
            if d['count'] >= 2
        ]

        # Average confidence
        confidences = [r.confidence for r in results if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7

        return {
            'grade': consensus_grade,
            'label': label,
            'confidence': round(avg_confidence, 2),
            'agreement': agreement,
            'defects': confirmed_defects
        }

    def _merge_comic_info(self, results: List[Dict]) -> Dict[str, Any]:
        """Merge comic_info from multiple providers"""
        merged = {}
        sources = {}

        for result in results:
            provider = result.get('provider', 'unknown')
            comic_info = result.get('comic_info', {})

            for key, value in comic_info.items():
                if key.startswith('_'):
                    continue
                if value and value not in [None, '', 'null', 'Unknown', 'unknown', []]:
                    if not merged.get(key):
                        merged[key] = value
                        sources[key] = [provider]
                    elif provider not in sources.get(key, []):
                        sources[key].append(provider)

        merged['_sources'] = sources
        return merged

    def _merge_key_issue_info(self, results: List[Dict]) -> Dict[str, Any]:
        """Merge key_issue_info from multiple providers"""
        is_key = False
        all_reasons = set()
        all_first_appearances = set()
        all_events = set()

        for result in results:
            key_info = result.get('key_issue_info', {})
            if key_info.get('is_key_issue'):
                is_key = True
            for reason in key_info.get('key_reasons', []):
                if reason:
                    all_reasons.add(reason)
            for char in key_info.get('first_appearances', []):
                if char:
                    all_first_appearances.add(char)
            for event in key_info.get('notable_events', []):
                if event:
                    all_events.add(event)

        return {
            'is_key_issue': is_key,
            'key_reasons': list(all_reasons),
            'first_appearances': list(all_first_appearances),
            'notable_events': list(all_events)
        }


# Global swarm instance
swarm_brain = SwarmBrain()


async def grade_with_swarm(
    image_base64: str,
    metadata: Optional[Dict] = None,
    full_research: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for swarm grading.

    Args:
        image_base64: Comic image as base64
        metadata: Optional known metadata
        full_research: Also run pricing/history research

    Returns:
        Complete grading and research results
    """
    if full_research:
        return await swarm_brain.full_comic_analysis(image_base64, metadata)
    else:
        return await swarm_brain.grade_comic(image_base64, metadata)
