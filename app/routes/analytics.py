"""Analytics routes."""
from flask import Blueprint, request, jsonify
from ..models import analytics
from ..models import account
from ..models import transaction

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/api/analytics/stats')
def get_stats():
    """Get financial statistics with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    # Get total balance
    total_balance = account.get_total_balance(account_types if account_types else None)
    
    # Get income/expense stats
    stats = analytics.get_stats(start_date, end_date, account_types)
    stats['total_balance'] = total_balance
    
    return jsonify(stats)


@analytics_bp.route('/api/analytics/charts')
def get_chart_data():
    """Get data for charts with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    def get_category_color(category_name, index):
        """Generate consistent colors for categories based on name and index."""
        # Expanded color palette with 36 distinct colors
        base_colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', 
            '#C9CBCF', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8C471', 
            '#82E0AA', '#F1948A', '#A9DFBF', '#F9E79F', '#AED6F1', '#F8D7DA',
            '#D5DBDB', '#FADBD8', '#E8DAEF', '#D6EAF8', '#D1F2EB', '#FCF3CF',
            '#EBDEF0', '#D6F9D6', '#FFE4E1', '#E0F2E7', '#FFF0F5', '#F0FFFF'
        ]
        
        if index < len(base_colors):
            return base_colors[index]
        else:
            # Generate additional colors using golden angle for good distribution
            hue = (index * 137.5) % 360
            saturation = 65 + (index % 3) * 10  # Vary saturation slightly
            lightness = 55 + (index % 4) * 5    # Vary lightness slightly
            return f'hsl({hue}, {saturation}%, {lightness}%)'
    
    # Category spending
    categories = analytics.get_category_spending(start_date, end_date, account_types)
    
    # Create consistent color mapping for all charts
    category_color_map = {}
    for i, category in enumerate(categories):
        category_color_map[category['category']] = get_category_color(category['category'], i)
    
    category_data = {
        'labels': [c['category'] for c in categories],
        'datasets': [{
            'data': [c['total'] for c in categories],
            'backgroundColor': [category_color_map[c['category']] for c in categories]
        }]
    }
    
    # Monthly trend
    trends = analytics.get_monthly_trend(start_date, end_date, account_types)
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
    accounts = account.get_all()
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
    category_trends = analytics.get_category_trends(start_date, end_date, account_types)
    
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
    sorted_months = sorted(list(months))[-12:]  # Last 12 months
    # Use same category order as pie chart for consistency
    all_categories = [c['category'] for c in categories if c['category'] in categories_set]
    # Add any remaining categories not in the main spending list
    remaining_categories = sorted(list(categories_set - set(all_categories)))
    all_categories.extend(remaining_categories)
    
    # Get monthly income data for the same period
    monthly_income = {}
    trends = analytics.get_monthly_trend(start_date, end_date, account_types)
    for trend in trends:
        if trend['month'] in sorted_months:
            monthly_income[trend['month']] = trend['income']
    
    category_trend_data = {
        'labels': sorted_months,
        'datasets': [],
        'monthly_income': [monthly_income.get(month, 0) for month in sorted_months]
    }
    
    for i, category in enumerate(all_categories):
        data = []
        for month in sorted_months:
            data.append(category_data_by_month.get(category, {}).get(month, 0))
        
        # Use consistent color - if category is in the main categories, use existing color, else generate new
        if category in category_color_map:
            color = category_color_map[category]
        else:
            # For categories not in main spending list, get color based on total index
            main_category_count = len([c for c in categories])
            new_index = main_category_count + remaining_categories.index(category)
            color = get_category_color(category, new_index)
        
        category_trend_data['datasets'].append({
            'label': category,
            'data': data,
            'borderColor': color,
            'backgroundColor': color + '40',  # Add transparency for bar chart
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
    
    transactions = transaction.get_by_category(
        category, start_date, end_date, account_types
    )
    
    return jsonify([dict(row) for row in transactions])


@analytics_bp.route('/api/analytics/income-transactions')
def get_income_transactions():
    """Get income transactions (excluding transfers) with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    transactions = transaction.get_income_transactions(
        start_date, end_date, account_types
    )
    
    return jsonify([dict(row) for row in transactions])


@analytics_bp.route('/api/analytics/top-payees')
def get_top_payees():
    """Get top payees by spending amount with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    limit = request.args.get('limit', 10, type=int)
    
    payees = analytics.get_top_payees(start_date, end_date, account_types, limit)
    
    return jsonify({
        'labels': [p['payee'] for p in payees],
        'datasets': [{
            'label': 'Amount Spent',
            'data': [p['total'] for p in payees],
            'backgroundColor': [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', 
                '#FF9F40', '#C9CBCF', '#FF6B6B', '#4ECDC4', '#45B7D1'
            ][:len(payees)]
        }]
    })


@analytics_bp.route('/api/analytics/savings-investments-flow')
def get_savings_investments_flow():
    """Get monthly savings and investments flow data with filters."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_types = request.args.getlist('account_types')
    
    flow_data = analytics.get_savings_investments_flow(start_date, end_date, account_types)
    
    if not flow_data:
        return jsonify({
            'labels': [],
            'datasets': [],
            'monthly_income': []
        })
    
    return jsonify({
        'labels': [f['month'] for f in flow_data],
        'datasets': [
            {
                'label': 'Savings Net',
                'data': [f['savings_net'] for f in flow_data],
                'backgroundColor': '#4BC0C0',
                'borderColor': '#4BC0C0',
                'borderWidth': 1
            },
            {
                'label': 'Investments Net',
                'data': [f['investments_net'] for f in flow_data],
                'backgroundColor': '#9966FF',
                'borderColor': '#9966FF',
                'borderWidth': 1
            },
            {
                'label': 'Other Outgoing',
                'data': [f['other_outgoing'] for f in flow_data],
                'backgroundColor': '#FF6384',
                'borderColor': '#FF6384',
                'borderWidth': 1
            }
        ],
        'monthly_income': [f['income'] for f in flow_data]
    })


@analytics_bp.route('/api/analytics/net-worth-history')
def get_net_worth_history():
    """Get net worth history over all time (ignoring date filters)."""
    history = analytics.get_net_worth_history()
    
    return jsonify({
        'labels': [h['month'] for h in history],
        'datasets': [{
            'label': 'Net Worth',
            'data': [h['net_worth'] for h in history],
            'borderColor': '#4BC0C0',
            'backgroundColor': 'rgba(75, 192, 192, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    })