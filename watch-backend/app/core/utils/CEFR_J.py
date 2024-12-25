from typing import List

import pandas as pd


def extract_cefr_wordlist(
    file_path: str, tabs: List[str], columns: List[str], output_csv_path: str
) -> None:
    """
    Extract specified columns from given tabs in an Excel file and save to a CSV file.

    Args:
        file_path (str): Path to the Excel file.
        tabs (List[str]): List of sheet names to extract data from.
        columns (List[str]): List of column names to extract.
        output_csv_path (str): Path to save the resulting CSV file.
    """
    combined_data = pd.DataFrame()

    for tab in tabs:
        try:
            # Load the sheet
            sheet_data = pd.read_excel(file_path, sheet_name=tab, usecols=columns)

            # Append to the combined DataFrame
            combined_data = pd.concat([combined_data, sheet_data], ignore_index=True)
        except Exception as e:
            print(f"Error processing tab '{tab}': {e}")

    # Save the combined data to a CSV file
    combined_data.to_csv(output_csv_path, index=False)
    print(f"Data has been successfully saved to {output_csv_path}")


# Example usage
if __name__ == "__main__":
    file_path = "../../resources/CEFR_J_Wordlist_1.6.xlsx"
    tabs = ["A1", "A2", "B1", "B2"]
    columns = ["headword", "pos", "CEFR"]
    output_csv_path = "../../resources/CEFR_combined_data.csv"
    extract_cefr_wordlist(file_path, tabs, columns, output_csv_path)
