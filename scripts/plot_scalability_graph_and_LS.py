import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('scripts/scalability_graph_LS.csv')
df_graph = df[['n_cases', 'runtime_seconds_graph']].dropna()
df_ls = df[['n_cases', 'runtime_seconds_LS']].dropna()

x_graph = df_graph['n_cases'].values
y_graph = df_graph['runtime_seconds_graph'].values
x_ls = df_ls['n_cases'].values
y_ls = df_ls['runtime_seconds_LS'].values

plt.figure(figsize=(14, 9))

X_graph_reshape = x_graph.reshape(-1, 1)

# Fit 2nd degree polynomial
poly_features_2 = PolynomialFeatures(degree=2, include_bias=False)
X_graph_poly_2 = poly_features_2.fit_transform(X_graph_reshape)
poly_model_2 = LinearRegression(fit_intercept=False)
poly_model_2.fit(X_graph_poly_2, y_graph)
b, a = poly_model_2.coef_[0], poly_model_2.coef_[1]
c = 0

# Fit 3rd degree polynomial
poly_features_3 = PolynomialFeatures(degree=3, include_bias=False)
X_graph_poly_3 = poly_features_3.fit_transform(X_graph_reshape)
poly_model_3 = LinearRegression(fit_intercept=False)
poly_model_3.fit(X_graph_poly_3, y_graph)
d3, c3, b3, a3 = poly_model_3.coef_[0], poly_model_3.coef_[1], poly_model_3.coef_[2], 0

X_ls_reshape = x_ls.reshape(-1, 1)
linear_model = LinearRegression(fit_intercept=False)
linear_model.fit(X_ls_reshape, y_ls)
d = linear_model.coef_[0]
e = 0

plt.scatter(x_graph, y_graph, alpha=0.6, label='Graph (actual)', color='blue', s=30)
plt.scatter(x_ls, y_ls, alpha=0.6, label='Local Search (actual)', color='red', s=30)

x_smooth = np.linspace(10, 2500, 1000)
X_smooth_reshape = x_smooth.reshape(-1, 1)

X_smooth_poly_2 = poly_features_2.transform(X_smooth_reshape)
y_poly_2 = poly_model_2.predict(X_smooth_poly_2)
X_smooth_poly_3 = poly_features_3.transform(X_smooth_reshape)
y_poly_3 = poly_model_3.predict(X_smooth_poly_3)
y_linear = linear_model.predict(X_smooth_reshape)

y_poly_2 = np.maximum(y_poly_2, 0)
y_poly_3 = np.maximum(y_poly_3, 0)

valid_idx_2 = y_poly_2 >= 0
if np.any(valid_idx_2):
    plt.plot(x_smooth[valid_idx_2], y_poly_2[valid_idx_2], 'b-', linewidth=2.5, label='Graph (2nd degree)', alpha=0.8)

valid_idx_3 = y_poly_3 >= 0
if np.any(valid_idx_3):
    plt.plot(x_smooth[valid_idx_3], y_poly_3[valid_idx_3], 'm-', linewidth=2.5, label='Graph (3rd degree)', alpha=0.8)
    
plt.plot(x_smooth, y_linear, 'r-', linewidth=2.5, label='Local Search (linear)', alpha=0.8)

A = a
B = b - d
C = c - e

discriminant = B**2 - 4*A*C

if discriminant >= 0 and A != 0:
    x1 = (-B + np.sqrt(discriminant)) / (2*A)
    x2 = (-B - np.sqrt(discriminant)) / (2*A)
    
    intersections = []
    for x_int in [x1, x2]:
        if 10 <= x_int <= 2500:
            y_int = d * x_int + e
            if y_int > 0:
                intersections.append((x_int, y_int))
    
    for i, (x_int, y_int) in enumerate(intersections):
        plt.plot(x_int, y_int, 'go', markersize=15, markeredgewidth=3, 
                markeredgecolor='darkgreen', label=f'Intersection: ({x_int:.1f}, {y_int:.2f})')
        
        plt.annotate(f'({x_int:.0f}, {y_int:.1f})', 
                    xy=(x_int, y_int), 
                    xytext=(x_int - 400, y_int + 50),
                    fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.3"))

plt.xlabel('Number of Cases', fontsize=14)
plt.ylabel('Runtime (seconds)', fontsize=14)
plt.title('Scalability Comparison: Graph vs Local Search', fontsize=16)
plt.legend(loc='upper left', bbox_to_anchor=(0.01, 0.83), fontsize=11, framealpha=0.9)

plt.xlim(0, 2600)
plt.ylim(0, None)

poly_eq_2 = f'Graph (2nd): y = {a:.2e}x² + {b:.2e}x'
poly_eq_3 = f'Graph (3rd): y = {b3:.2e}x³ + {c3:.2e}x² + {d3:.2e}x'
linear_eq = f'Local Search: y = {d:.2e}x'
equation_text = poly_eq_2 + '\n' + poly_eq_3 + '\n' + linear_eq

r2_poly_2 = r2_score(y_graph, poly_model_2.predict(X_graph_poly_2))
r2_poly_3 = r2_score(y_graph, poly_model_3.predict(X_graph_poly_3))
r2_linear = r2_score(y_ls, linear_model.predict(X_ls_reshape))
equation_text += f'\n\nR² Graph (2nd): {r2_poly_2:.4f}'
equation_text += f'\nR² Graph (3rd): {r2_poly_3:.4f}'
equation_text += f'\nR² Local Search: {r2_linear:.4f}'

plt.text(0.02, 0.98, equation_text, transform=plt.gca().transAxes, 
         verticalalignment='top', fontfamily='monospace', fontsize=10,
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
plt.savefig('scalability_comparison.png', dpi=150, bbox_inches='tight')