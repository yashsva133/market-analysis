with open('apps/web/src/app/page.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

workspaces = ['dashboard', 'companies', 'company', 'events', 'news', 'screener', 'research', 'scenario', 'watchlist', 'portfolio', 'technicals', 'calendar', 'compare', 'models', 'quant', 'explorer', 'sources', 'alerts']
for w in workspaces:
    matches = [i+1 for i, line in enumerate(lines) if f'"{w}"' in line and 'activeTab' in line]
    print(f"{w:12}: {matches}")
