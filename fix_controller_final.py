
import os

file_location = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

# Read the file
with open(file_location, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Warning: line numbers in list are 0-indexed.
# view_file lines are 1-indexed.
# Line 1046 in view_file = index 1045 in list.
# Line 1098 in view_file = index 1097 in list.

start_index = 1045
# Find where the next method starts to be safe.
# Look for "_process_tabulation_phase"
end_index = -1
for i in range(start_index, len(lines)):
    if 'def _process_tabulation_phase' in lines[i]:
        end_index = i
        break

if end_index == -1:
    print("Could not find _process_tabulation_phase, aborting.")
    exit(1)

print(f"Replacing lines {start_index} to {end_index} (exclusive)")

# New method content
new_method = '''  async def _process_cordis_api_phase(self, courses_in_range: List[Tuple[str, str, str, str]], search_mode: str = 'broad', progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
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

# Construct new lines
final_lines = lines[:start_index] + [new_method] + lines[end_index:]

# Now detect where to truncate at the end (remove duplicates appended)
# Look for the SECOND occurrence of "_process_cordis_api_phase" which should be near the end.
# Actually, I know I appended it after "return []" of run_scraping.
# run_scraping ends around 1525 (in original file, indices might have shifted).
# But wait, lines list still has old content.
# I need to find where run_scraping ends in `final_lines` and truncate after that.

# Find "def run_scraping"
run_scraping_index = -1
for i, line in enumerate(final_lines):
    if 'def run_scraping' in line:
        run_scraping_index = i
        break

if run_scraping_index != -1:
    # Find the end of run_scraping. It ends with "return []".
    # Assuming it's the last "return []" before the duplicates or EOF?
    # The file had duplicates APended.
    # So if I find the FIRST "return []" inside/after run_scraping that is indented correctly?
    
    # Let's just look for the line that was 1525: "          return []" (10 spaces).
    # And truncate immediately after it.
    
    truncation_index = -1
    for i in range(run_scraping_index, len(final_lines)):
        if 'return []' in final_lines[i] and final_lines[i].strip() == 'return []':
             # Check indentation if possible, but 'strip' removes it.
             # Just assume the first return [] after run_scraping is the end of the method.
             # Actually, run_scraping has multiple returns? 
             # No, looking at view_file, it has "return []" at 1323 (early exit) and 1525 (end) and 1515 (return processed_results).
             # The one at the very end is inside except block.
             
             # Let's verify context.
             # The end of the file (before my appends) was:
             # 1522: if progress_callback:
             # 1523:    progress_callback...
             # 1524: 
             # 1525:    return []
             
             # So safely, I can iterate and find the one followed by the duplicate method definition?
             # Or just find the line index that corresponds to the old line 1525.
             pass
    
    # Better strategy: Loop backwards from end.
    # If I see "def _process_cordis_api_phase", it is a duplicate (since we replaced the one at top).
    # Valid one is at index `start_index`.
    # Any usage of "def _process_cordis_api_phase" AFTER `start_index + 1` is a duplicate.
    
    # Re-scan final_lines for duplicates
    # We inserted new_method at start_index.
    # So final_lines has the correct method there.
    # Any subsequent occurence should be removed.
    
    full_content = "".join(final_lines)
    # This is risky if I just string manipulation.
    
    # Let's stick to list manipulation.
    # The new method inserted is one string element in the list.
    
    # Iterate from end of list.
    for i in range(len(final_lines) - 1, start_index + 1, -1):
        if 'def _process_cordis_api_phase' in final_lines[i]:
            print(f"Found duplicate at index {i}, truncating file before this.")
            # We want to remove this and everything after?
            # Or just this method?
            # I appended to the VERY end. So I can truncate AT this index.
            # But wait, there might be empty lines before it.
            # The "return []" was the end of valid code.
            
            # Let's find "return []" of run_scraping and truncate AFTER it.
            # But I need to identify WHICH return [].
            
            # Let's go with: Remove all lines after the last "return []" that belongs to run_scraping.
            pass

    # Alternative:
    # 1. Write the `final_lines` to a temp string.
    # 2. Find the index of "async def run_scraping".
    # 3. Find the matching end of run_scraping (indented return []).
    # 4. Cut off everything after.
    
    pass

# Simplified Truncation Logic:
# The valid file ends with the `run_scraping` method.
# usage of `truncate_and_fix.py` relied on hardcoded line number 1526.
# Since I am replacing lines in the middle, the line numbers shift.
# length of new_method vs old lines 1046-1098.
# old lines count: 1098 - 1046 = 52 lines.
# new_method count: ~53 lines.
# So the shift is small.

# Logic:
# 1. Identify where `run_scraping` starts.
# 2. Iterate lines starting from there.
# 3. Find the signature `def _process_cordis_api_phase`.
# 4. If found, truncate the list at that index (minus formatting lines).

output_lines = []
found_run_scraping = False
truncated = False

for line in final_lines:
    if 'def run_scraping' in line:
        found_run_scraping = True
    
    if found_run_scraping and 'def _process_cordis_api_phase' in line:
        print("Found duplicate appended method. stopping write.")
        truncated = True
        break
    
    output_lines.append(line)

with open(file_location, 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("Saved fixed file.")
