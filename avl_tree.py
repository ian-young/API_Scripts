"""
Author: Ian Young
Purpose: Serve as a module to import for creating, sorting, and manipulating
AVL trees for code optimization.
"""
# Import essential libraries
from anytree import Node, RenderTree


class TreeNode():
    """
    Represents a node in an AVL tree.

    Attributes:
    * left: A pointer to the left child node.
    * right: A pointer to the right child node.
    * value: The value of the current node.
    * height: The height of the current node in the AVL tree.
    """

    def __init__(self, key):
        """
        Initializes a new tree node with the given key.

        :param key: The value of the node.
        :type key: Any
        """
        self.left = None
        self.right = None
        self.value = key
        self.height = 1  # Initialize the height to 1 for a new node
        self.balance_factor = 0


def insert_avl(current_node, key):
    """
    Inserts a new key into the AVL tree rooted at 'current_node'.

    :param current_node: The current node in the AVL tree.
    :type current_node: TreeNode or None
    :param key: The key to be inserted.
    :type key: Any
    :return: The modified current node after the insertion.
    :rtype: TreeNode
    """
    if current_node is None:
        return TreeNode(key)

    if key < current_node.value:
        current_node.left = insert_avl(current_node.left, key)
    else:
        current_node.right = insert_avl(current_node.right, key)

    # Update the height of the current node
    current_node.height = 1 + \
        max(height(current_node.left), height(current_node.right))

    # Perform AVL tree rotations to maintain balance
    balance = balance_factor(current_node)

    # Left Heavy
    if balance > 1:
        # Right Heavy
        if key < current_node.left.value:
            return rotate_right(current_node)

        # Left-Right Heavy
        if key > current_node.left.value:
            current_node.left = rotate_left(current_node.left)
            return rotate_right(current_node)

    # Right Heavy
    if balance < -1:
        # Left Heavy
        if key > current_node.right.value:
            return rotate_left(current_node)

        # Right-Left Heavy
        if key < current_node.right.value:
            current_node.right = rotate_right(current_node.right)
            return rotate_left(current_node)

    return current_node


def build_avl_tree(arr):
    """
    Builds an AVL tree from an array of strings.

    :param arr: The array of strings to be inserted into the tree.
    :type arr: List[str]
    :return: The root of the built AVL tree.
    :rtype: TreeNode or None
    """
    root = None
    for value in arr:
        root = insert_avl(root, value)
    return root


def search_in_avl_tree(current_node, key):
    """
    Searches for a key in the AVL tree rooted at 'current_node'.

    :param current_node: The current node in the AVL tree.
    :type current_node: TreeNode or None
    :param key: The key to be searched for.
    :type key: Any
    :return: The node containing the key or None if the key is not found.
    :rtype: TreeNode or None
    """
    if current_node is None or current_node.value == key:
        return current_node
    if key < current_node.value:
        return search_in_avl_tree(current_node.left, key)
    return search_in_avl_tree(current_node.right, key)


def search_in_avl_tree(current_node, key):
    """
    Searches for a key in the AVL tree rooted at 'current_node'.

    :param current_node: The current node in the AVL tree.
    :type current_node: TreeNode or None
    :param key: The key to be searched for.
    :type key: Any
    :return: The node containing the key or None if the key is not found.
    :rtype: TreeNode or None
    """
    if current_node is None or current_node.value == key:
        return current_node
    if key < current_node.value:
        return search_in_avl_tree(current_node.left, key)
    return search_in_avl_tree(current_node.right, key)


def avl_tree_to_anytree(root):
    """
    Converts an AVL tree to an AnyTree representation.

    :param root: The root node of the AVL tree.
    :type root: TreeNode or None
    :return: The root node of the equivalent AnyTree representation.
    :rtype: Node or None
    """
    if root is None:
        return None

    node = Node(str(root.value), balance_factor=root.balance_factor)

    # Use a list for children attribute
    children = []

    # Check for left and right child nodes before extending
    if root.left is not None:
        children.extend([avl_tree_to_anytree(root.left)])
    if root.right is not None:
        children.extend([avl_tree_to_anytree(root.right)])

    node.children = children

    return node


def print_avl_tree_anytree(root):
    """
    Prints the AVL tree using the AnyTree representation.

    :param root: The root node of the AVL tree.
    :type root: TreeNode or None
    """
    avl_tree = avl_tree_to_anytree(root)
    for pre, _, node in RenderTree(avl_tree):
        print(f"{pre}{node.name} (BF: {node.balance_factor})")


def height(node):
    """
    Get the height of a node in the AVL tree.

    :param node: The node in the AVL tree.
    :type node: TreeNode or None
    :return: The height of the node.
    :rtype: int
    """
    if node is None:
        return 0
    return node.height


def update_height(node):
    """
    Update the height of a node in the AVL tree.

    :param node: The node in the AVL tree.
    :type node: TreeNode or None
    """
    if node is not None:
        node.height = 1 + max(height(node.left), height(node.right))


def balance_factor(node):
    """
    Get the balance factor of a node in the AVL tree.

    :param node: The node in the AVL tree.
    :type node: TreeNode or None
    :return: The balance factor of the node.
    :rtype: int
    """
    if node is None:
        return 0
    return height(node.left) - height(node.right)


def rotate_right(y):
    """
    Perform a right rotation in the AVL tree.

    :param y: The node to be rotated.
    :type y: TreeNode
    :return: The new root after the rotation.
    :rtype: TreeNode
    """
    x = y.left
    t2 = x.right

    x.right = y
    y.left = t2

    update_height(y)
    update_height(x)

    y.balance_factor = balance_factor(y)
    x.balance_factor = balance_factor(x)

    return x


def rotate_left(x):
    """
    Perform a left rotation in the AVL tree.

    :param x: The node to be rotated.
    :type x: TreeNode
    :return: The new root after the rotation.
    :rtype: TreeNode
    """
    y = x.right
    t2 = y.left

    y.left = x
    x.right = t2

    update_height(x)
    update_height(y)

    x.balance_factor = balance_factor(x)
    y.balance_factor = balance_factor(y)

    return y
