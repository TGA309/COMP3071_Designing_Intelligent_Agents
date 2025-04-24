import time
import datetime
from typing import Dict, List, Any, Optional, Union
from crawler.llm_processing import evaluate_responses
from crawler.logger import setup_logger

class TimeMetric:
    """Measure and record time metrics for crawling or retrieval operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.logger = setup_logger()
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        self.logger.info(f"Time measurement started at: {datetime.datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        return self
    
    def stop(self):
        """Stop the timer and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.logger.info(f"Time measurement stopped. Duration: {self.duration:.2f} seconds")
        return self.duration
    
    def get_metrics(self) -> Dict[str, float]:
        """Return time metrics."""
        if self.duration is None:
            self.logger.warning("Attempting to get time metrics before timer has been stopped")
            return {"error": "Timer has not been stopped"}
        
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration,
            "formatted_duration": str(datetime.timedelta(seconds=self.duration))
        }

class HarvestRatio:
    """
    Tracks and calculates harvest ratios at different crawl depths and cumulatively.
    Harvest ratio = number of relevant pages / number of pages crawled
    """
    
    def __init__(self):
        self.depth_metrics = {}
        self.cache_metrics = {"relevant": 0, "total": 0}
        self.logger = setup_logger()
    
    def record_page(self, depth, page_score, depth_threshold, is_processed=True):
        """
        Record a processed page at a specific depth
        
        Args:
            depth: The crawl depth of the page
            page_score: The relevance score of the page
            depth_threshold: The relevance threshold for this depth
            is_processed: Whether the page was successfully processed
        """
        # Initialize metrics for this depth if it does not exist
        if depth not in self.depth_metrics:
            self.depth_metrics[depth] = {"relevant": 0, "total": 0}
        
        # Always increment total counter if the page was processed
        if is_processed:
            self.depth_metrics[depth]["total"] += 1
            
            # Increment relevance counter if score meets the threshold
            if page_score >= depth_threshold:
                self.depth_metrics[depth]["relevant"] += 1
                self.logger.debug(f"Relevant page found at depth {depth}: score={page_score:.3f}, threshold={depth_threshold:.3f}")
    
    def record_cache_access(self, results, base_relevance_threshold):
        """
        Record pages retrieved from cache
        
        Args:
            results: List of results retrieved from cache
            base_relevance_threshold: The base relevance threshold to determine relevance
        """
        if not results:
            return
            
        self.cache_metrics["total"] += len(results)
        relevant_count = sum(1 for r in results if r.get('weighted_score', 0) >= base_relevance_threshold)
        self.cache_metrics["relevant"] += relevant_count
        
        self.logger.info(f"Cache access: {relevant_count} relevant results out of {len(results)} total")
    
    def get_depth_harvest_ratio(self, depth):
        """Get harvest ratio for a specific depth"""
        if depth not in self.depth_metrics or self.depth_metrics[depth]["total"] == 0:
            return 0.0
            
        return self.depth_metrics[depth]["relevant"] / self.depth_metrics[depth]["total"]
    
    def get_cumulative_harvest_ratio(self):
        """Get cumulative harvest ratio across all depths"""
        total_relevant = sum(metrics["relevant"] for metrics in self.depth_metrics.values())
        total_pages = sum(metrics["total"] for metrics in self.depth_metrics.values())
        
        if total_pages == 0:
            return 0.0
            
        return total_relevant / total_pages
    
    def get_cache_harvest_ratio(self):
        """Get harvest ratio for cache access"""
        if self.cache_metrics["total"] == 0:
            return 0.0
            
        return self.cache_metrics["relevant"] / self.cache_metrics["total"]
    
    def get_overall_harvest_ratio(self):
        """Get overall harvest ratio including both crawled pages and cache access"""
        total_relevant = sum(metrics["relevant"] for metrics in self.depth_metrics.values()) + self.cache_metrics["relevant"]
        total_pages = sum(metrics["total"] for metrics in self.depth_metrics.values()) + self.cache_metrics["total"]
        
        if total_pages == 0:
            return 0.0
            
        return total_relevant / total_pages
    
    def get_metrics(self):
        """Get complete harvest ratio metrics"""
        per_depth_ratios = {depth: self.get_depth_harvest_ratio(depth) for depth in self.depth_metrics}
        
        metrics = {
            "per_depth": {
                depth: {
                    "relevant_pages": self.depth_metrics[depth]["relevant"],
                    "total_pages": self.depth_metrics[depth]["total"],
                    "harvest_ratio": ratio
                } for depth, ratio in per_depth_ratios.items()
            },
            "cache": {
                "relevant_pages": self.cache_metrics["relevant"],
                "total_pages": self.cache_metrics["total"],
                "harvest_ratio": self.get_cache_harvest_ratio()
            },
            "cumulative": {
                "relevant_pages": sum(metrics["relevant"] for metrics in self.depth_metrics.values()),
                "total_pages": sum(metrics["total"] for metrics in self.depth_metrics.values()),
                "harvest_ratio": self.get_cumulative_harvest_ratio()
            },
            "overall": {
                "relevant_pages": sum(metrics["relevant"] for metrics in self.depth_metrics.values()) + self.cache_metrics["relevant"],
                "total_pages": sum(metrics["total"] for metrics in self.depth_metrics.values()) + self.cache_metrics["total"],
                "harvest_ratio": self.get_overall_harvest_ratio()
            }
        }
        
        return metrics


class GenerativeAIScoring:
    """Use the existing evaluate_responses function from LLM processing pipeline for generative AI scoring."""
    
    def __init__(self):
        self.logger = setup_logger()
    
    def calculate(self, original_prompt: str, crawled_results: List[Dict[str, Any]], 
                 llm_response: str) -> Dict[str, Any]:
        """
        Calculate generative AI scoring using the evaluate_responses function.
        
        Args:
            original_prompt: The original user query
            crawled_results: List of crawled content
            llm_response: Generated response from LLM
            
        Returns:
            Evaluation metrics from evaluate_responses
        """
        self.logger.info("Performing generative AI scoring evaluation...")
        evaluation_results = evaluate_responses(original_prompt, crawled_results, llm_response)
        self.logger.info("Generative AI scoring evaluation completed")
        return evaluation_results

class EvaluationMetrics:
    """
    Comprehensive evaluation metrics combining time, harvest ratio, and generative AI scoring.
    """
    
    def __init__(self):
        """
        Initialize the evaluation metrics with components.
        
        Args:
            relevance_threshold: Threshold for harvest ratio calculation
        """
        self.time_metric = TimeMetric()
        self.harvest_ratio = HarvestRatio()
        self.generative_ai_scoring = GenerativeAIScoring()
        self.logger = setup_logger()
    
    def start_timer(self):
        """Start the timer for crawling or retrieval operation."""
        self.logger.info("Starting evaluation timer")
        return self.time_metric.start()
    
    def stop_timer(self):
        """Stop the timer."""
        self.logger.info("Stopping evaluation timer")
        return self.time_metric.stop()
    
    def evaluate(self, original_prompt: str, crawled_results: List[Dict[str, Any]],
             llm_response: str = None, harvest_ratio_metrics=None) -> Dict[str, Any]:
        """
        Perform comprehensive evaluation of crawling and optional LLM response.
        
        Args:
            original_prompt: The original user query
            crawled_results: List of crawled content with relevance scores
            total_pages_visited: Total number of pages visited during crawling
            llm_response: Optional generated response from LLM
            
        Returns:
            Dictionary with comprehensive evaluation metrics
        """
        self.logger.info(f"Starting comprehensive evaluation for prompt: '{original_prompt}'")
        
        time_metrics = self.time_metric.get_metrics()
    
        # Use provided metrics or default to internal instance
        if harvest_ratio_metrics:
            harvest_metrics = harvest_ratio_metrics
        else:
            harvest_metrics = self.harvest_ratio.get_metrics()
        
        eval_metrics = {
            "time_metrics": time_metrics,
            "harvest_metrics": harvest_metrics,
        }
        
        if llm_response:
            self.logger.info("LLM response provided, performing generative AI scoring")
            gen_ai_metrics = self.generative_ai_scoring.calculate(
                original_prompt, crawled_results, llm_response
            )
            eval_metrics["generative_ai_scoring_metrics"] = gen_ai_metrics
        else:
            self.logger.info("No LLM response provided, skipping generative AI scoring")
        
        self.logger.info("Comprehensive evaluation completed")
        return eval_metrics