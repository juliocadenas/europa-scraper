
import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Truncate after line 1526 (index 1526, since 0-indexed)
# Line 1526 in view_file usage was empty line after "return []"
# Check content to be sure
# Line 1525 was "return []"
# Keep lines up to 1526 (inclusive)
kept_lines = lines[:1526]

# Verify last line is what we expect
print(f"Last kept line: {repr(kept_lines[-1])}")

# New method content with 2 spaces def, 6 spaces body
new_method = '''
  async def _process_cordis_api_phase(self, courses_in_range: List[Tuple[str, str, str, str]], search_mode: str = 'broad', progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
      """
      Executes the search phase using the Cordis Europa API.
      """
      all_search_results = []
      total_courses = len(courses_in_range)
      current_course = 0
      
      logger.info(f"=== PHASE 1: SEARCHING RESULTS with CORDIS EUROPA API (Mode: {search_mode}) ===")
      logger.info(f"Total courses to process in search: {total_courses}")
      
      for sic_code, course_name, status, server in courses_in_range:
          if self.stop_requested:
              logger.info("Scraping stopped by user during search phase")
              break
              
          current_course += 1
          self.progress_reporter.set_course_counts(current_course, total_courses)
          current_course_info = f"{sic_code} - {course_name}"
          
          if progress_callback:
              progress_callback(0, f"Searching course {current_course} of {total_courses} - {current_course_info}", self.stats)
              
          search_term = course_name if course_name else sic_code
          
          # CRITICAL SANITIZATION: Remove prefixes like "101.0 - " or "123 - " that break exact search
          # User has courses like "101.0 - Iron ore mining". We search only for "Iron ore mining".
          # UPDATED: The hyphen is optional for cases like "101.0 Iron mining"
          search_term = re.sub(r'^[\\d.]+\\s*[-–]?\\s*', '', search_term).strip()
          
          logger.info(f"Searching in Cordis API: '{search_term}' (Original: '{course_name if course_name else sic_code}')")
          
          try:
              # Pass search_mode to the API client
              results = await self.cordis_api_client.search_projects_and_publications(search_term, search_mode=search_mode)
              
              for r in results:
                  r['sic_code'] = sic_code
                  r['course_name'] = course_name
                  r['search_term'] = search_term
                  all_search_results.append(r)
                  
              self.stats['total_urls_found'] += len(results)
              logger.info(f"Found {len(results)} results in Cordis API for '{search_term}'")
              
              if progress_callback:
                  progress_callback(0, f"Searching course {current_course} of {total_courses} - {current_course_info} | Found: {len(results)} results", self.stats)
                  
          except Exception as e:
              logger.error(f"Error in Cordis API search for '{search_term}': {e}")
              self.stats['total_errors'] += 1
              continue
              
      return all_search_results
'''

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(kept_lines)
    f.write(new_method)

print("Truncated and appended new method.")
