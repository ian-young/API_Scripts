"""
Author: Ian Young
Purpose: Practice creating graphs in Python.
"""
import matplotlib.pyplot as plt

# Sample data
categories = ['Category A', 'Category B', 'Category C', 'Category D']
values = [25, 50, 30, 45]

# Creating a bar graph
plt.bar(categories, values, color='blue')

# Adding labels and title
plt.xlabel('Categories')
plt.ylabel('Values')
plt.title('Bar Graph Example')

# Display the graph
plt.show()
