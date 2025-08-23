# 💰 Money Tracker

A simple personal finance tool to track finances in multiple accounts.

Supports different account types
 - current
 - savings
 - investement

 Has categories for each transactions, these can also be assigned to projects to track how much a project or holiday costs.

 All saved to a sqlite database, and is automaticaly backed up. Can also import and export to a csv.


## 🚀 Getting Started

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. **Download app image**
   download and run app image from release page

Or from source

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd moneyapp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

### Running Options

The application supports multiple running modes:

#### Browser Mode 
```bash
python main.py --mode browser
```
- Opens automatically in your default web browser
- Accessible at `http://localhost:5000` (or alternative is that is in use)

#### Desktop Window Mode (Default)
```bash
python moneytrack.py --mode window
```
- Runs as a desktop application 

#### Headless Mode
```bash
python moneytrack.py --mode headless
```
- Access manually at `http://localhost:5000`


## 💡 Usage

### Adding Accounts
1. Click "Add Account" in the sidebar
2. Choose account type (checking, savings, credit, investment)
3. Set initial balance if needed

### Recording Transactions
1. Select the account from the dropdown
2. Enter amount (positive for income, negative for expenses)
3. Choose transaction type
4. Add payee, category, and notes as needed
5. For transfers, select destination account

### Setting Up Recurring Transactions
1. Go to the "Recurring" tab
2. Set up transactions with frequency (daily, weekly, monthly, etc.)
3. The system will automatically process due recurring transactions

### Importing Data
1. Go to "Settings" tab
2. Use "Import CSV" to upload bank transaction files
3. The system automatically detects transfers and categorizes transactions
4. Supports common CSV formats from major banks

### Analytics
1. Visit the "Analytics" tab for financial insights
2. Use date range filters to analyze specific periods
3. Click on chart elements for detailed breakdowns
4. Filter by account types for targeted analysis

## 🗄️ Database Structure

The application uses SQLite with the following main tables:
- **accounts**: Bank accounts with types and balances
- **transactions**: All financial transactions
- **recurring_transactions**: Templates for recurring transactions
- **payees**: List of transaction payees
- **categories**: Expense and income categories
- **Projects**: Groups of transactions for projects



## 📝 License

This project is open source and available under the [MIT License](LICENSE).


## 📦 Standalone Application Packaging

Transform your Money Tracker into standalone applications for easy distribution across platforms.

### Prerequisites for Packaging
```bash
pip install pyinstaller
```

### Build Process

In the scripts directory 

#### 1. Build Executable
```bash
./build.sh
```
Creates a standalone executable in `dist/MoneyTracker`

#### 2. Create AppImage (Linux)
```bash
./build_appimage.sh
```
Generates `MoneyTracker-x86_64.AppImage` for Linux distribution

### Installation & Usage
1. **Direct Executable**: `./dist/MoneyTracker`
2. **AppImage**: `chmod +x MoneyTracker-x86_64.AppImage && ./MoneyTracker-x86_64.AppImage`

All standalone versions include the complete Python runtime and dependencies - no separate Python installation required!

