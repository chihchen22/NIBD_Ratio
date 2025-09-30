# Quick Start Guide: Adding Your Files

This guide will help you add your CSV data, Python code, and documentation to this repository.

## 1. Adding Your CSV Data File

1. Place your CSV file in the `data/` directory:
   ```bash
   # Copy your file to the data directory
   cp /path/to/your/data.csv data/nibd_calibration_data.csv
   ```

2. Verify the file is properly formatted:
   ```bash
   # Check the first few lines
   head data/nibd_calibration_data.csv
   ```

3. Commit the data file:
   ```bash
   git add data/nibd_calibration_data.csv
   git commit -m "Add calibration data CSV file"
   ```

## 2. Adding Your Python Code

### Option A: Replace the Template
If your Perplexity AI generated code is a complete model script:

1. Replace the template in `src/model.py` with your code:
   ```bash
   cp /path/to/your/code.py src/model.py
   ```

2. Update file paths in your code to use the repository structure:
   - Data files should reference: `../data/` or use the DATA_DIR variable
   - Output should go to: `../outputs/` or use the OUTPUT_DIR variable

### Option B: Add as New File
If you want to keep multiple files:

1. Add your code as a new file:
   ```bash
   cp /path/to/your/code.py src/nibd_model_perplexity.py
   ```

2. Keep the template for reference

### Testing Your Code

1. Make sure all dependencies are available:
   ```bash
   pip install -r requirements.txt
   ```

2. Run your code:
   ```bash
   python src/model.py
   # or
   python src/nibd_model_perplexity.py
   ```

3. If you get import errors, add missing packages to `requirements.txt`

## 3. Adding Your Documentation

1. Place your model development document in the `docs/` directory:
   ```bash
   cp /path/to/your/document.pdf docs/model_development.pdf
   # or for Word documents
   cp /path/to/your/document.docx docs/model_development.docx
   # or for Markdown
   cp /path/to/your/document.md docs/model_development.md
   ```

2. If you have multiple documents, add them all:
   ```bash
   cp /path/to/methodology.pdf docs/
   cp /path/to/data_dictionary.xlsx docs/
   ```

## 4. Update the Main README

After adding your files, update the main README.md to reflect:
- What data files are included
- How to run your specific code
- What documentation is available

Example addition to README.md:
```markdown
## Available Data
- `data/nibd_calibration_data.csv` - Historical NIBD ratio data with economic indicators

## Running the Model
```bash
python src/model.py --data data/nibd_calibration_data.csv
```

## Documentation
- `docs/model_development.pdf` - Complete model development methodology
```

## 5. Commit All Changes

Once you've added all files:

```bash
# Check what files are new/changed
git status

# Add all new files
git add data/ src/ docs/ requirements.txt

# Commit with a descriptive message
git commit -m "Add calibration data, model code, and documentation"

# Push to GitHub
git push
```

## Common Adjustments for Perplexity AI Code

Perplexity AI generated code may need these adjustments:

1. **File Paths**: Update hardcoded paths to use relative paths
   ```python
   # Change from:
   df = pd.read_csv('/absolute/path/data.csv')
   
   # To:
   from pathlib import Path
   DATA_DIR = Path(__file__).parent.parent / "data"
   df = pd.read_csv(DATA_DIR / 'nibd_calibration_data.csv')
   ```

2. **Dependencies**: Add any missing imports to `requirements.txt`

3. **Configuration**: Extract hardcoded values to a config section or separate config file

4. **Error Handling**: Add try-except blocks for file operations and data loading

5. **Output Directories**: Ensure output directories are created before saving files
   ```python
   os.makedirs('outputs', exist_ok=True)
   ```

## Need Help?

- Check the README files in each directory for more specific guidance
- Ensure your Python environment is set up correctly
- Verify all file paths are relative to the repository root
