import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

logger = logging.getLogger(__name__)

class ResultManager:
    """
    Manages scraping results and storage.
    """
    
    def __init__(self):
        """Initialize the result manager."""
        self.results = []
        self.omitted_results = []
        self.output_file = ""
        self.omitted_file = ""
    
    def initialize_output_files(self, from_sic: str, to_sic: str, from_course: str, to_course: str, search_engine: str = '', worker_id: Optional[int] = None) -> tuple[str, str]:
        """
        Initializes output files for results and omitted results.
        
        Args:
            from_sic: Starting SIC code
            to_sic: Ending SIC code
            from_course: Starting course name
            to_course: Ending course name
            search_engine: The search engine being used
            worker_id: Optional identifier for parallel workers
            
        Returns:
            Tuple of (output_file, omitted_file)
        """
        # Sanitize course names for use in filenames
        from_course_sanitized = '_'.join(from_course.split()[:2]) if from_course else ''
        to_course_sanitized = '_'.join(to_course.split()[:2]) if to_course else ''
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Add search engine to filename
        engine_str = f"_{search_engine.replace(' ', '_').lower()}" if search_engine else ''
        
        # Add worker ID to filename if provided
        worker_str = f"_worker_{worker_id}" if worker_id is not None else ""

        # Define base filename
        base_filename = f"{from_sic}_{from_course_sanitized}_to_{to_sic}_{to_course_sanitized}{engine_str}{worker_str}_{timestamp}"

        # Create EN directory by default for main output
        base_results_dir = 'results'
        en_dir = os.path.join(base_results_dir, 'EN')
        os.makedirs(en_dir, exist_ok=True)
        
        # Create output file path inside EN subfolder
        self.output_file = os.path.join(
            en_dir, 
            f"results_{base_filename}.csv"
        )
        
        # Create empty CSV file with predefined columns
        columns = [
            'sic_code', 'course_name', 'title', 
            'description', 'url', 'total_words', 'lang'
        ]
        pd.DataFrame(columns=columns).to_csv(self.output_file, index=False)
        
        logger.info(f"CSV file created for worker {worker_id} in EN folder: {self.output_file}")
        
        # Create directory for omitted results
        omitted_dir = 'omitidos'
        os.makedirs(omitted_dir, exist_ok=True)
        
        # Create omitted file path
        self.omitted_file = os.path.join(
            omitted_dir, 
            f"omitidos_{base_filename}.xlsx"
        )
        
        logger.info(f"File for omitted results for worker {worker_id}: {self.omitted_file}")
        
        return self.output_file, self.omitted_file
    
    def add_result(self, result: Dict[str, Any]) -> bool:
        """
        Adds a result to the results list and CSV file, routing to language folder if needed.
        
        Args:
            result: Result dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to results list
            self.results.append(result)
            
            # Add to CSV file
            return self.append_to_csv(result)
        except Exception as e:
            logger.error(f"Error adding result: {str(e)}")
            return False

    def _get_file_path_for_lang(self, lang: str) -> str:
        """Helper to get or create file path for a specific language."""
        lang = lang.lower() if lang else 'en'
        
        # Consistent routing: results/[LANG.upper()]/results_..._[lang].csv
        
        # Initialize lang_files map if needed
        if not hasattr(self, 'lang_files'):
            self.lang_files = {}
            
        # If it's English and we already set output_file, use it (it's already in results/EN/)
        if lang == 'en':
            return self.output_file
            
        if lang in self.lang_files:
            return self.lang_files[lang]
            
        # Create new path: results/ES/results_..._es.csv
        try:
            # Base results directory is the parent of the EN folder
            en_dir_path = os.path.dirname(self.output_file)
            base_results_dir = os.path.dirname(en_dir_path)
            lang_dir = os.path.join(base_results_dir, lang.upper())
            os.makedirs(lang_dir, exist_ok=True)
            
            # Construct filename based on main filename
            main_name = os.path.basename(self.output_file)
            name_parts = os.path.splitext(main_name)
            new_name = f"{name_parts[0]}_{lang}{name_parts[1]}"
            
            lang_file_path = os.path.join(lang_dir, new_name)
            
            # Initialize with headers if new
            if not os.path.exists(lang_file_path):
                columns = [
                    'sic_code', 'course_name', 'title', 
                    'description', 'url', 'total_words', 'lang'
                ]
                pd.DataFrame(columns=columns).to_csv(lang_file_path, index=False)
                logger.info(f"Created new language result file: {lang_file_path}")
                
            self.lang_files[lang] = lang_file_path
            return lang_file_path
            
        except Exception as e:
            logger.error(f"Error creating file for lang {lang}: {e}")
            return self.output_file # Fallback to main

    def append_to_csv(self, result: Dict[str, Any]) -> bool:
        """
        Appends a result to the appropriate CSV file based on language.
        
        Args:
            result: Result dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            lang = result.get('lang', 'en')
            target_file = self._get_file_path_for_lang(lang)
            
            df = pd.DataFrame([result])
            # Ensure 'lang' column exists in dataframe used for appending
            if 'lang' not in df.columns:
                 df['lang'] = lang
            
            # Append without writing header
            df.to_csv(target_file, mode='a', header=False, index=False)
            return True
        except Exception as e:
            logger.error(f"Error appending to CSV: {str(e)}")
            return False
    
    def save_omitted_to_excel(self) -> str:
        """
        Saves omitted results to an Excel file.
        
        Returns:
            Path to the saved file
        """
        try:
            if not self.omitted_results:
                logger.warning("No omitted results to save")
                
                # Even if there are no results, ensure we create an empty Excel file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # If self.omitted_file is not set, create a default path
                if not self.omitted_file:
                    omitted_dir = 'omitidos'
                    os.makedirs(omitted_dir, exist_ok=True)
                    self.omitted_file = os.path.join(omitted_dir, f"omitidos_{timestamp}.xlsx")
                
                # Create an empty Excel file
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Omitted Results"
                
                # Add a note that there are no omitted results
                ws.cell(row=1, column=1, value="No se omitieron resultados durante el proceso.")
                
                # Ensure the output directory exists
                output_dir = os.path.dirname(self.omitted_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    logger.info(f"Omitted directory created: {output_dir}")
                
                # Save the file
                wb.save(self.omitted_file)
                logger.info(f"Empty omitted results file created at: {self.omitted_file}")
                
                return self.omitted_file
            
            # Create a new workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Omitted Results"
            
            # Define styles
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="0066CC", end_color="0066CC", fill_type="solid")
            
            # Add headers
            headers = ['Código SIC', 'Nombre del Curso', 'Título', 'URL', 'Descripción', 'Razón de Omisión']
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Add data
            for row_num, result in enumerate(self.omitted_results, 2):
                ws.cell(row=row_num, column=1, value=result.get('sic_code', ''))
                ws.cell(row=row_num, column=2, value=result.get('course_name', ''))
                ws.cell(row=row_num, column=3, value=result.get('title', ''))
                ws.cell(row=row_num, column=4, value=result.get('url', ''))
                ws.cell(row=row_num, column=5, value=result.get('description', ''))
                ws.cell(row=row_num, column=6, value=result.get('omission_reason', ''))
            
            # Adjust column widths
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                adjusted_width = (max_length + 2) if max_length < 50 else 50
                ws.column_dimensions[column].width = adjusted_width
            
            # Ensure the output directory exists
            output_dir = os.path.dirname(self.omitted_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Omitted directory created: {output_dir}")
            
            # Get absolute path
            abs_output_file = os.path.abspath(self.omitted_file)
            
            # Save to Excel
            wb.save(self.omitted_file)
            
            logger.info(f"Saved {len(self.omitted_results)} omitted results to {abs_output_file}")
            
            return abs_output_file
            
        except Exception as e:
            logger.error(f"Error saving omitted results to Excel: {str(e)}")
            return ""
    
    def get_results(self) -> List[Dict[str, Any]]:
        """
        Gets the list of results.
        
        Returns:
            List of result dictionaries
        """
        return self.results
    
    def get_omitted_results(self) -> List[Dict[str, Any]]:
        """
        Gets the list of omitted results.
        
        Returns:
            List of omitted result dictionaries
        """
        return self.omitted_results
    
    def get_output_file(self) -> str:
        """
        Gets the output file path.
        
        Returns:
            Output file path
        """
        return self.output_file
    
    def get_omitted_file(self) -> str:
        """
        Gets the omitted file path.
        
        Returns:
            Omitted file path
        """
        return self.omitted_file
