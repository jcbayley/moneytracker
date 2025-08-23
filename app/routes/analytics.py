"""Analytics routes."""
from flask import Blueprint, request, jsonify
from ..models.analytics import AnalyticsModel
from ..models.account import AccountModel
from ..models.transaction import TransactionModel

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/api/analytics/stats')
def get_stats():
    """Get financial statistics with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    # Get total balance
    total_balance = AccountModel.get_total_balance(account_types if account_types else None)
    
    # Get income/expense stats
    stats = AnalyticsModel.get_stats(start_date, end_date, account_types)
    stats['total_balance'] = total_balance
    
    return jsonify(stats)


@analytics_bp.route('/api/analytics/charts')
def get_chart_data():
    """Get data for charts with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    # Category spending
    categories = AnalyticsModel.get_category_spending(start_date, end_date, account_types)
    category_data = {
        'labels': [c['category'] for c in categories],
        'datasets': [{
            'data': [c['total'] for c in categories],
            'backgroundColor': [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
            ][:len(categories)]
        }]
    }
    
    # Monthly trend
    trends = AnalyticsModel.get_monthly_trend(start_date, end_date, account_types)
    trend_data = {
        'labels': [t['month'] for t in trends],
        'datasets': [
            {
                'label': 'Income',
                'data': [t['income'] for t in trends],
                'borderColor': '#36A2EB',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'tension': 0.4
            },
            {
                'label': 'Expenses',
                'data': [t['expenses'] for t in trends],
                'borderColor': '#FF6384',
                'backgroundColor': 'rgba(255, 99, 132, 0.1)',
                'tension': 0.4
            },
            {
                'label': 'Savings',
                'data': [t['savings'] for t in trends],
                'borderColor': '#4BC0C0',
                'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                'tension': 0.4
            },
            {
                'label': 'Investments',
                'data': [t['investments'] for t in trends],
                'borderColor': '#9966FF',
                'backgroundColor': 'rgba(153, 102, 255, 0.1)',
                'tension': 0.4
            }
        ]
    }
    
    # Account balances
    accounts = AccountModel.get_all()
    if account_types:
        accounts = [a for a in accounts if a['type'] in account_types]
    
    account_data = {
        'labels': [a['name'] for a in accounts],
        'datasets': [{
            'label': 'Balance',
            'data': [a['balance'] for a in accounts],
            'backgroundColor': ['#36A2EB' if a['balance'] >= 0 else '#FF6384' for a in accounts]
        }]
    }
    
    # Category trends
    category_trends = AnalyticsModel.get_category_trends(start_date, end_date, account_types)
    
    # Organize by category and month
    category_data_by_month = {}
    months = set()
    categories_set = set()
    
    for row in category_trends:
        month = row['month']
        category = row['category']
        total = row['total']
        
        months.add(month)
        categories_set.add(category)
        
        if category not in category_data_by_month:
            category_data_by_month[category] = {}
        category_data_by_month[category][month] = total
    
    # Convert to chart format
    sorted_months = sorted(list(months))[-6:]  # Last 6 months
    all_categories = sorted(list(categories_set))
    
    category_trend_data = {
        'labels': sorted_months,
        'datasets': []
    }
    
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384']
    
    for i, category in enumerate(all_categories):
        data = []
        for month in sorted_months:
            data.append(category_data_by_month.get(category, {}).get(month, 0))
        
        category_trend_data['datasets'].append({
            'label': category,
            'data': data,
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)] + '20',
            'tension': 0.4
        })
    
    return jsonify({
        'category': category_data,
        'trend': trend_data,
        'accounts': account_data,
        'category_trends': category_trend_data
    })


@analytics_bp.route('/api/analytics/category/<category>')
def get_category_transactions(category):
    """Get transactions for a specific category with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    transactions = TransactionModel.get_by_category(
        category, start_date, end_date, account_types
    )
    
    return jsonify([dict(row) for row in transactions])