# Money Tracker

A simple personal finance tool to track finances in multiple current/savings/investement accounts.

Supports different account types
 - current
 - savings
 - investment

 Has categories for each transactions, these can also be assigned to projects to track how much a project or holiday costs.

 Includes AI-powered transaction querying to analyze spending patterns and get insights about your financial data.

 All saved to a sqlite database, and is automatically backed up. Can also import and export to a csv. 

Backend written in python with flask.
Frontend html/javascript then run with PyQT and webview in application, or can use browser if server is running headless.

**Security Note:** This application stores data unencrypted in a local SQLite database and includes minimal security features. It is designed for personal use on trusted, local systems only. Use at your own discretion.

## Demo

<div align="center">
  <table>
    <tr>
      <td align="center">
        <b>Light Theme</b><br>
        <img src="docs/transactions_light.png" alt="Light Theme" width="400">
      </td>
      <td align="center">
        <b>Dark Theme</b><br>
        <img src="docs/transactions.png" alt="Dark Theme" width="400">
      </td>
    </tr>
    <tr>
      <td align="center">
        <b>Analytics Dashboard</b><br>
        <img src="docs/analytics1.png" alt="Analytics Overview" width="400">
      </td>
      <td align="center">
        <b>Extended Analytics</b><br>
        <img src="docs/analytics2.png" alt="Extended Analytics" width="400">
      </td>
    </tr>
    <tr>
      <td align="center">
        <b>AI Query Interface</b><br>
        <img src="docs/ai-query.png" alt="AI Query Interface" width="400">
      </td>
      <td align="center">
        <b>AI Query Response</b><br>
        <img src="docs/ai-query-return.png" alt="AI Query Response" width="400">
      </td>
    </tr>
  </table>
</div>

For more screenshots and detailed views, see the [documentation](docs/README.md).

## Getting Started

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

## How to Run

### Option 1: Download AppImage
Download and run the AppImage from the release page.

### Option 2: Run from Source
```bash
git clone <repository-url>
cd moneyapp
pip install -r requirements.txt
python main.py
```

### Option 3: Run Headless with Browser
```bash
python main.py --mode headless
```
Then open your browser and navigate to `http://localhost:5000`

## License

This project is open source and available under the [MIT License](LICENSE).

## Building

### Build Executable
```bash
./scripts/build.sh
```

### Build AppImage
```bash
./scripts/build_appimage.sh
```

