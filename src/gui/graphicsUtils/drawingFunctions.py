import matplotlib.pyplot as plt

# Function to draw a point defined by a clumn vector
def drawPoint(vector, ax=None, size=3, color='k'):
    if ax is None:
        ax = plt.gca()    
    ax.scatter(vector[0], vector[1], vector[2], size=size, color=color)

# Function to draw consecutive segments given the points. The line is left open
def drawSegmentsOpen(points, ax=None, linewidth=2, color='gray', linestyle='-', marker='.', markerSize=3):
    if ax is None:
        ax = plt.gca()    

    for i in range(1,len(points)):
        ax.plot( [points[0,i-1], points[0,i]], 
                [points[1,i-1], points[1,i]], 
                [points[2,i-1], points[2,i]], 
                linewidth=linewidth, 
                linestyle=linestyle,
                color=color,
                marker=marker,
                markerfacecolor=color,
                markersize=markerSize
                )
        
# Function to draw consecutive segments given the points. The line is closed
def drawSegmentsClosed(points, ax=None, linewidth=2, color='gray', linestyle='-', marker='.', markerSize=3):
    if ax is None:
        ax = plt.gca()   

    # Call the open function
    drawSegmentsOpen(points, ax, linewidth, color, linestyle, marker, markerSize)

    # Close the line
    ax.plot( [points[0,-1], points[0,0]], 
            [points[1,-1], points[1,0]], 
            [points[2,-1], points[2,0]], 
            linewidth=linewidth, 
            linestyle=linestyle,
            color=color,
            marker=marker,
            markerfacecolor=color,
            markersize=markerSize
            )
