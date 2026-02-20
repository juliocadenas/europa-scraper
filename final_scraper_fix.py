
import os
import re

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
methods_seen = set()
skip_mode = False
class_name = "ScraperController"

for i, line in enumerate(lines):
    # Detect method definitions
    match = re.search(r'^\s+async def (\w+)|^\s+def (\w+)', line)
    if match:
        method_name = match.group(1) or match.group(2)
        if method_name in methods_seen and method_name != "__init__": # Allow init if needed but usually just one
            print(f"Skipping duplicate method: {method_name} at line {i+1}")
            skip_mode = True
        else:
            methods_seen.add(method_name)
            skip_mode = False
            
            # Apply specific fixes to the kept method signatures
            if method_name == "_process_single_result":
                line = "  async def _process_single_result(self, result: Dict[str, Any], min_words: int, search_engine: str, require_keywords: bool = False) -> Optional[Dict[str, Any]]:\n"
            elif method_name == "_process_cordis_api_phase":
                line = "  async def _process_cordis_api_phase(self, courses_in_range: List[Tuple[str, str, str, str]], search_mode: str = 'broad', progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:\n"
            elif method_name == "_process_tabulation_phase":
                line = "  async def _process_tabulation_phase(self, all_search_results: List[Dict[str, Any]], total_courses: int, min_words: int, search_engine: str, progress_callback: Optional[Callable] = None, require_keywords: bool = False) -> List[Dict[str, Any]]:\n"
    
    # Check if we should stop skipping (if we hit a new method that is NOT a duplicate)
    # But wait, skip_mode should only stop when we hit the NEXT method.
    # The logic above already handles match. So if match is found while skip_mode is True,
    # the logic above will decide whether to stay in skip_mode or not.
    
    if not skip_mode:
        # Apply body fixes
        if "_process_single_result(result, min_words, search_engine)" in line:
            # Fix call site in _process_tabulation_phase
            line = line.replace("_process_single_result(result, min_words, search_engine)", "_process_single_result(result, min_words, search_engine, require_keywords=require_keywords)")
        
        if "results = await self.cordis_api_client.search_projects_and_publications(search_term)" in line:
            # Fix call site in _process_cordis_api_phase
            line = line.replace("search_projects_and_publications(search_term)", "search_projects_and_publications(search_term, search_mode=search_mode)")
        
        if "processed_results = await self._process_tabulation_phase(all_search_results, total_courses, min_words, search_engine, progress_callback)" in line:
            # Fix call site in run_scraping
            line = line.replace("_process_tabulation_phase(all_search_results, total_courses, min_words, search_engine, progress_callback)", "_process_tabulation_phase(all_search_results, total_courses, min_words, search_engine, progress_callback, require_keywords=require_keywords)")
            # Also ensure require_keywords is defined before
            prefix = "          require_keywords = params.get('require_keywords', False)\n"
            new_lines.append(prefix)

        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("ScraperController.py fixed surgically.")
