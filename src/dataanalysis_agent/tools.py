"""This module provides tools for data analysis functionality.

It includes tools for loading CSV files and executing Python code for data analysis.
"""

import io
import sys
import contextlib
from typing import Any, Callable, List
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


# Global variable to store the dataframe
df = None


async def load_csv(file_path: str) -> str:
    """Load a CSV file into a pandas DataFrame.
    
    Args:
        file_path: Path to the CSV file to load.
    """
    global df
    try:
        # Check if file exists
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."
        
        # Load the CSV file
        df = pd.read_csv(file_path)
        
        # Get basic info about the dataframe
        info = f"Successfully loaded CSV file '{file_path}'\n"
        info += f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
        info += f"Columns: {', '.join(df.columns.tolist())}\n"
        info += f"Data types:\n{df.dtypes.to_string()}"
        
        return info
    except Exception as e:
        return f"Error loading CSV file: {str(e)}"


async def load_excel(file_path: str, sheet_name: str = None) -> str:
    """Load an Excel file into a pandas DataFrame.
    
    Args:
        file_path: Path to the Excel file to load.
        sheet_name: Name of the sheet to load. If None, loads the first sheet.
    """
    global df
    try:
        # Check if file exists
        if not Path(file_path).exists():
            return f"Error: File '{file_path}' not found."
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
            return f"Error: File '{file_path}' is not an Excel file. Supported extensions: .xlsx, .xls, .xlsm, .xlsb"
        
        # Load the Excel file
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheet_info = f" from sheet '{sheet_name}'"
        else:
            # Load first sheet by default
            df = pd.read_excel(file_path)
            # Get the actual sheet name that was loaded
            excel_file = pd.ExcelFile(file_path)
            sheet_info = f" from sheet '{excel_file.sheet_names[0]}' (first sheet)"
            
            # If multiple sheets exist, list them
            if len(excel_file.sheet_names) > 1:
                sheet_info += f"\nAvailable sheets: {', '.join(excel_file.sheet_names)}"
        
        # Get basic info about the dataframe
        info = f"Successfully loaded Excel file '{file_path}'{sheet_info}\n"
        info += f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
        info += f"Columns: {', '.join(df.columns.tolist())}\n"
        info += f"Data types:\n{df.dtypes.to_string()}"
        
        return info
    except ValueError as e:
        if "Worksheet" in str(e):
            # Get list of available sheets
            try:
                excel_file = pd.ExcelFile(file_path)
                return f"Error: {str(e)}\nAvailable sheets: {', '.join(excel_file.sheet_names)}"
            except:
                return f"Error loading Excel file: {str(e)}"
        return f"Error loading Excel file: {str(e)}"
    except Exception as e:
        return f"Error loading Excel file: {str(e)}"


async def python_repl(code: str) -> str:
    """Execute Python code for data analysis.
    
    This tool allows execution of Python code with access to pandas and the loaded dataframe.
    The dataframe is available as 'df' in the execution context.
    
    Args:
        code: Python code to execute.
    """
    global df
    
    # Check if dataframe is loaded
    if df is None:
        return "Error: No dataframe loaded. Please load a CSV file first using the load_csv tool."
    
    # Create a string buffer to capture output
    output_buffer = io.StringIO()
    
    # Create a context manager to capture stdout
    @contextlib.contextmanager
    def capture_output():
        old_stdout = sys.stdout
        try:
            sys.stdout = output_buffer
            yield
        finally:
            sys.stdout = old_stdout
    
    try:
        # Set up matplotlib for non-interactive backend
        plt.switch_backend('Agg')
        
        # Set up Korean font for matplotlib
        import matplotlib.font_manager as fm
        
        # Get list of available fonts
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        # Priority list of Korean fonts to try
        korean_fonts = [
            'AppleGothic',  # macOS
            'Apple SD Gothic Neo',  # macOS alternative
            'NanumGothic',  # Linux/common
            'Malgun Gothic',  # Windows
            'NanumBarunGothic',  # Linux alternative
            'UnDotum',  # Linux alternative
        ]
        
        # Find the first available Korean font
        font_set = False
        for font in korean_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = font
                font_set = True
                break
        
        # If no Korean font found, use default with warning
        if not font_set:
            plt.rcParams['font.family'] = 'DejaVu Sans'
            print("Warning: No Korean font found. Korean text may not display correctly.")
        
        # Prevent minus sign from appearing as box
        plt.rcParams['axes.unicode_minus'] = False
        
        # Apply font settings to seaborn as well
        sns.set_theme(font=plt.rcParams['font.family'], rc={'axes.unicode_minus': False})
        
        # Execute the code with pandas and numpy available
        with capture_output():
            # Create a local namespace with common imports
            local_namespace = {
                'df': df,
                'pd': pd,
                'np': np,  # numpy imported directly
                'plt': plt,
                'sns': sns,
            }
            
            # Execute the code
            exec(code, local_namespace)
            
            # If the last line is an expression, try to evaluate and print it
            lines = code.strip().split('\n')
            if lines:
                last_line = lines[-1].strip()
                # Check if it's likely an expression (not an assignment or statement)
                if (not any(last_line.startswith(kw) for kw in ['import', 'from', 'def', 'class', 'if', 'for', 'while', 'with', 'try']) 
                    and '=' not in last_line 
                    and last_line):
                    try:
                        result = eval(last_line, local_namespace)
                        if result is not None:
                            # If result is a DataFrame, convert to HTML automatically
                            if isinstance(result, pd.DataFrame):
                                print(result.to_html())
                            else:
                                print(result)
                    except:
                        pass
        
        # Get the output
        output = output_buffer.getvalue()
        
        # Check if there are any matplotlib figures
        figures = plt.get_fignums()
        if figures:
            # Create a directory for images
            plots_dir = Path("/tmp/dataanalysis_plots")
            plots_dir.mkdir(exist_ok=True)
            
            # Save all figures as PNG files
            plot_outputs = []
            
            for idx, fig_num in enumerate(figures):
                fig = plt.figure(fig_num)
                # Generate unique filename with timestamp
                from datetime import datetime
                import uuid
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"plot_{timestamp}_{unique_id}.png"
                filepath = plots_dir / filename
                
                # Save the figure
                fig.savefig(filepath, format='png', bbox_inches='tight', dpi=100)
                plt.close(fig)
                
                # Output markdown with local server URL
                # This assumes the plot server is running on port 8001
                plot_url = f"http://localhost:8001/{filename}"
                plot_outputs.append(f'![Visualization {idx + 1}]({plot_url})')
            
            # Add plots to output
            if plot_outputs:
                if output:
                    output += "\n\n"
                output += "<!-- VISUALIZATION OUTPUT -->\n"
                output += "\n".join(plot_outputs)
                output += "\n<!-- END VISUALIZATION OUTPUT -->"
        
        # If no output was produced, return a success message
        if not output:
            return "Code executed successfully (no output produced)."
        
        return output
        
    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        # Clean up any remaining plots
        plt.close('all')


TOOLS: List[Callable[..., Any]] = [load_csv, load_excel, python_repl]
