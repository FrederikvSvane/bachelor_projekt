import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Rectangle

# Set up the figure with 3 subplots
fig = plt.figure(figsize=(15, 6))

# 1D Simplex Example
ax1 = fig.add_subplot(131)
# Constraints: 0 ≤ x₁ ≤ 3
# Objective: maximize x₁

# Show as a horizontal line
line_y = 0.5
ax1.plot([0, 4], [line_y, line_y], 'k-', linewidth=1, alpha=0.3)

# Feasible region on the line
ax1.plot([0, 3], [line_y, line_y], 'b-', linewidth=8, alpha=0.5, label='Feasible region')

# Corner points
ax1.plot([0, 3], [line_y, line_y], 'ro', markersize=12, label='Corner points', zorder=5)

# Optimal solution
ax1.plot(3, line_y, 'go', markersize=14, label='Optimal solution', zorder=6)

# Objective function values at different points
for x_val in [0, 1, 2, 3]:
    ax1.plot([x_val, x_val], [line_y - 0.05, line_y + 0.05], 'k-', linewidth=1)
    ax1.text(x_val, line_y - 0.15, f'{x_val}', ha='center', fontsize=9)

# Objective function gradient arrow (extends from 0 to optimal point 3)
ax1.arrow(0, line_y + 0.2, 3, 0, head_width=0.08, head_length=0.15, 
          fc='darkgreen', ec='darkgreen', alpha=0.7)
ax1.text(1.5, line_y + 0.35, 'Objective: max x₁', fontsize=10, ha='center')

# Labels for corner points
ax1.text(0, line_y + 0.15, '(0)', ha='center', fontsize=9, color='red')
ax1.text(3, line_y + 0.15, '(3)', ha='center', fontsize=9, color='green', fontweight='bold')

ax1.set_xlim(-0.5, 4)
ax1.set_ylim(0, 1)
ax1.set_xlabel('x₁', fontsize=12)
ax1.set_title('1D Linear Programming', fontsize=12, fontweight='bold')
ax1.set_yticks([])  # Remove y-axis ticks
ax1.grid(True, alpha=0.3, axis='x')

# 2D Simplex Example
ax2 = fig.add_subplot(132)
# Constraints: x₁ ≤ 3, x₂ ≤ 3, x₁ ≥ 0, x₂ ≥ 0 (simple square)
# Objective: maximize x₁ + x₂

# Draw axes
ax2.axhline(y=0, color='black', linewidth=0.5)
ax2.axvline(x=0, color='black', linewidth=0.5)

# Define feasible region as a simple square
vertices = np.array([[0, 0], [3, 0], [3, 3], [0, 3]])
feasible = plt.Polygon(vertices, alpha=0.3, color='lightblue', label='Feasible region')
ax2.add_patch(feasible)

# Plot corner points
ax2.plot([0, 3, 3, 0], [0, 0, 3, 3], 'ro', markersize=10, label='Corner points')

# Add annotations for corner points
for vertex in vertices:
    ax2.annotate(f'({vertex[0]},{vertex[1]})', (vertex[0], vertex[1]), 
                xytext=(5, 5), textcoords='offset points', fontsize=8)

# Optimal solution (at vertex [3, 3] since we're maximizing x₁ + x₂)
ax2.plot(3, 3, 'go', markersize=12, label='Optimal solution', zorder=5)

# Objective function contours
x_obj = np.linspace(0, 4, 100)
y_obj = np.linspace(0, 4, 100)
X, Y = np.meshgrid(x_obj, y_obj)
Z = X + Y
contours = ax2.contour(X, Y, Z, levels=[2, 4, 6], colors='green', alpha=0.6)
ax2.clabel(contours, inline=True, fontsize=8)

# Add simplex algorithm path arrows
# Step 1: (0,0) -> (3,0)
ax2.arrow(0, 0, 2.7, 0, head_width=0.15, head_length=0.2, 
          fc='darkgreen', ec='darkgreen', alpha=0.8, linewidth=2)
# Step 2: (3,0) -> (3,3)
ax2.arrow(3, 0, 0, 2.7, head_width=0.15, head_length=0.2, 
          fc='darkgreen', ec='darkgreen', alpha=0.8, linewidth=2)

# Add step labels
ax2.text(1.5, -0.3, 'Step 1', fontsize=9, ha='center', color='darkgreen')
ax2.text(3.3, 1.5, 'Step 2', fontsize=9, ha='center', color='darkgreen')
ax2.text(1.5, 3.5, 'Objective: max x₁ + x₂', fontsize=10, ha='center')

ax2.set_xlim(-0.5, 4)
ax2.set_ylim(-0.5, 4)
ax2.set_xlabel('x₁', fontsize=12)
ax2.set_ylabel('x₂', fontsize=12)
ax2.set_title('2D Linear Programming', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)

# 3D Simplex Example
ax3 = fig.add_subplot(133, projection='3d')
# Constraints: x₁ ≤ 3, x₂ ≤ 3, x₃ ≤ 3, x₁,x₂,x₃ ≥ 0 (simple cube)
# Objective: maximize x₁ + x₂ + x₃

# Define vertices of a simple cube
vertices_3d = np.array([
    [0, 0, 0], [3, 0, 0], [0, 3, 0], [0, 0, 3],
    [3, 3, 0], [3, 0, 3], [0, 3, 3], [3, 3, 3]
])

# Define faces of the cube
faces = [
    [0, 1, 4, 2],  # bottom face
    [1, 5, 7, 4],  # right face
    [2, 4, 7, 6],  # back face
    [0, 2, 6, 3],  # left face
    [0, 1, 5, 3],  # front face
    [3, 5, 7, 6]   # top face
]

# Create the 3D polygon collection for feasible region (cube)
poly3d = [[vertices_3d[vertex] for vertex in face] for face in faces]
face_collection = Poly3DCollection(poly3d, alpha=0.3, facecolor='lightblue', 
                                  edgecolor='blue', label='Feasible region')
ax3.add_collection3d(face_collection)

# Plot corner points (excluding optimal solution)
# All corner points except [3, 3, 3]
corner_mask = ~((vertices_3d[:, 0] == 3) & (vertices_3d[:, 1] == 3) & (vertices_3d[:, 2] == 3))
corner_points = vertices_3d[corner_mask]
ax3.scatter(corner_points[:, 0], corner_points[:, 1], corner_points[:, 2], 
           c='red', s=80, label='Corner points')

# Optimal solution (at vertex [3, 3, 3] since we're maximizing x₁ + x₂ + x₃)
ax3.scatter([3], [3], [3], c='green', s=120, marker='o', label='Optimal solution')

# Add coordinate axes
ax3.plot([0, 4], [0, 0], [0, 0], 'k-', linewidth=0.5)
ax3.plot([0, 0], [0, 4], [0, 0], 'k-', linewidth=0.5)
ax3.plot([0, 0], [0, 0], [0, 4], 'k-', linewidth=0.5)

# Add labels for key vertices
ax3.text(0, 0, 0, '(0,0,0)', fontsize=8)
ax3.text(3, 3, 3, '(3,3,3)', fontsize=8, color='green', fontweight='bold')

# Objective function planes (showing level sets)
# For objective function x₁ + x₂ + x₃ = constant, we have x₃ = constant - x₁ - x₂
x_range = np.linspace(-0.5, 3.5, 20)
y_range = np.linspace(-0.5, 3.5, 20)
X, Y = np.meshgrid(x_range, y_range)

# Draw objective function planes that extend beyond the cube for cleaner visualization
for obj_val in [3, 6, 9]:
    Z = obj_val - X - Y  # From x₁ + x₂ + x₃ = obj_val
    # Only show where the plane makes sense (Z is reasonable)
    mask = (Z >= -0.5) & (Z <= 3.5)
    Z_masked = np.where(mask, Z, np.nan)
    ax3.plot_surface(X, Y, Z_masked, alpha=0.2, color='green', 
                    rstride=2, cstride=2, linewidth=0, antialiased=True)

# Add simplex algorithm path arrows
# Step 1: (0,0,0) -> (3,0,0)
ax3.quiver(0, 0, 0, 3, 0, 0, color='darkgreen', alpha=0.8, 
          arrow_length_ratio=0.15, linewidth=3)
# Step 2: (3,0,0) -> (3,3,0)
ax3.quiver(3, 0, 0, 0, 3, 0, color='darkgreen', alpha=0.8, 
          arrow_length_ratio=0.15, linewidth=3)
# Step 3: (3,3,0) -> (3,3,3)
ax3.quiver(3, 3, 0, 0, 0, 3, color='darkgreen', alpha=0.8, 
          arrow_length_ratio=0.15, linewidth=3)

# Add step labels
ax3.text(1.5, 0, -0.3, 'Step 1', fontsize=8, color='darkgreen')
ax3.text(3.3, 1.5, -0.3, 'Step 2', fontsize=8, color='darkgreen')
ax3.text(3.3, 3.3, 1.5, 'Step 3', fontsize=8, color='darkgreen')
ax3.text(1.5, 1.5, 3.8, 'Objective: max x₁+x₂+x₃', fontsize=10)

ax3.set_xlim(0, 4)
ax3.set_ylim(0, 4)
ax3.set_zlim(0, 4)
ax3.set_xlabel('x₁', fontsize=12)
ax3.set_ylabel('x₂', fontsize=12)
ax3.set_zlabel('x₃', fontsize=12)
ax3.set_title('3D Linear Programming', fontsize=12, fontweight='bold')
ax3.view_init(elev=20, azim=45)

# Create custom legends below each subplot
plt.tight_layout()

# Add legends below the plots
fig.text(0.17, -0.05, 'Legend: ', fontsize=10, fontweight='bold', ha='center')
fig.text(0.17, -0.10, '● Feasible region  ● Corner points  ● Optimal solution', 
         fontsize=9, ha='center', 
         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.3))

fig.text(0.5, -0.05, 'Legend: ', fontsize=10, fontweight='bold', ha='center')
fig.text(0.5, -0.10, '● Feasible region  ● Constraints  ● Corner points  ● Optimal solution  ━ Objective contours', 
         fontsize=9, ha='center',
         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.3))

fig.text(0.83, -0.05, 'Legend: ', fontsize=10, fontweight='bold', ha='center')
fig.text(0.83, -0.10, '● Feasible region  ● Corner points  ● Optimal solution  ▬ Objective planes', 
         fontsize=9, ha='center',
         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.3))

plt.subplots_adjust(bottom=0.15)
plt.show()

# Add a text explanation
print("Simplex Algorithm Visualization:")
print("=" * 50)
print("1D: The feasible region is a line segment. The algorithm checks both endpoints.")
print("   Optimal solution found at x₁ = 3")
print()
print("2D: The feasible region is a square. The simplex path: (0,0) → (3,0) → (3,3)")
print("   Optimal solution found at (x₁, x₂) = (3, 3) with objective value = 6")
print()
print("3D: The feasible region is a cube. The simplex path: (0,0,0) → (3,0,0) → (3,3,0) → (3,3,3)")
print("   Optimal solution found at (x₁, x₂, x₃) = (3, 3, 3) with objective value = 9")
print()
print("Key insight: The simplex algorithm exploits the fact that the optimal solution")
print("always occurs at a vertex (corner point) of the feasible region.")