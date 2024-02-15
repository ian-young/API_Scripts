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


def insert_avl_from_dict(current_node, data, key):
    """
    Inserts data from a dictionary into the AVL tree rooted at 'current_node'.

    :param current_node: The current node in the AVL tree.
    :type current_node: TreeNode or None
    :param data: The dictionary containing data to be inserted.
    :type data: dict
    :param key: The key value that is used for sorting.
    :type: Any
    :return: The modified current node after the insertion.
    :rtype: TreeNode
    """
    if key not in data:
        return current_node

    key_value = data[key]
    if current_node is None:
        return TreeNode(data)

    if key_value < current_node.value[key]:
        current_node.left = insert_avl_from_dict(current_node.left, data, key)
    else:
        current_node.right = insert_avl_from_dict(
            current_node.right, data, key)

    # Update the height of the current node
    current_node.height = 1 + \
        max(height(current_node.left), height(current_node.right))

    # Perform AVL tree rotations to maintain balance
    balance = balance_factor(current_node)

    # Left Heavy
    if balance > 1:
        # Right Heavy
        if key_value < current_node.left.value[key]:
            return rotate_right(current_node)

        # Left-Right Heavy
        if key_value > current_node.left.value[key]:
            current_node.left = rotate_left(current_node.left)
            return rotate_right(current_node)

    # Right Heavy
    if balance < -1:
        # Left Heavy
        if key_value > current_node.right.value[key]:
            return rotate_left(current_node)

        # Right-Left Heavy
        if key_value < current_node.right.value[key]:
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


def build_avl_tree_from_dict(data_list, key):
    """
    Builds an AVL tree from a list of dictionaries.

    :param data_list: The list of dictionaries to be inserted into the tree.
    :type data_list: List[dict]
    :return: The root of the built AVL tree.
    :rtype: TreeNode or None
    """
    root = None
    for data in data_list:
        root = insert_avl_from_dict(root, data, key)
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
    if current_node is None or current_node.value == \
            key:
        return current_node
    if key < current_node.value:
        return search_in_avl_tree(current_node.left, key)
    return search_in_avl_tree(current_node.right, key)


def search_in_avl_tree_dict(root, key, target_value):
    """
    Searches for a node in the AVL tree with the specified key and target value.

    :param root: The root node of the AVL tree.
    :type root: TreeNode or None
    :param key: The key to search for ('person_id' in this case).
    :type key: str
    :param target_value: The target value to search for.
    :type target_value: Any
    :return: The node with the specified key and target value, or None if not found.
    :rtype: TreeNode or None
    """
    if root is None:
        return None

    current_node = root
    while current_node:
        current_key_value = current_node.value.get(key)
        if target_value == current_key_value:
            return current_node
        elif target_value < current_key_value:
            current_node = current_node.left
        else:
            current_node = current_node.right

    return None


def remove_common_nodes(tree1, tree2):
    """
    Removes nodes from tree1 that are present in tree2 based on the specified key.

    :param tree1: The root node of the first AVL tree.
    :type tree1: TreeNode or None
    :param tree2: The root node of the second AVL tree.
    :type tree2: TreeNode or None
    :return: The modified root node of tree1.
    :rtype: TreeNode or None
    """
    if tree1 is None:
        return None

    # Traverse the entire tree and identify common nodes
    common_nodes = find_common_nodes_array(tree1, tree2, set())

    # Remove common nodes in a bottom-up manner
    return remove_nodes_array(tree1, common_nodes)


def find_common_nodes_array(tree1, tree2, common_nodes):
    """
    Helper function to find common nodes in tree1 and tree2.

    :param tree1: The root node of the first AVL tree.
    :type tree1: TreeNode or None
    :param tree2: The root node of the second AVL tree.
    :type tree2: TreeNode or None
    :param common_nodes: Set to store common nodes.
    :type common_nodes: set
    :return: Set of common nodes.
    :rtype: set
    """
    if tree1 is not None:
        # Check if the current node is present in tree2
        if search_in_avl_tree(tree2, tree1.value):
            common_nodes.add(tree1.value)

        # Traverse left and right subtrees
        find_common_nodes_array(tree1.left, tree2, common_nodes)
        find_common_nodes_array(tree1.right, tree2, common_nodes)

    return common_nodes


def remove_nodes_array(tree1, common_nodes):
    """
    Helper function to remove common nodes from tree1.

    :param tree1: The root node of the first AVL tree.
    :type tree1: TreeNode or None
    :param common_nodes: Set of common nodes.
    :type common_nodes: set
    :return: The modified root node of tree1.
    :rtype: TreeNode or None
    """
    if tree1 is None:
        return None

    # Remove nodes in the left subtree
    tree1.left = remove_nodes_array(tree1.left, common_nodes)

    # Remove nodes in the right subtree
    tree1.right = remove_nodes_array(tree1.right, common_nodes)

    # Check if the current node is present in common_nodes
    if tree1.value in common_nodes:
        if tree1.left is None and tree1.right is None:
            return None  # Node found in common_nodes and has no children, remove it from tree1
        elif tree1.left is None:
            return tree1.right  # Node found in common_nodes and has only a right child
        elif tree1.right is None:
            return tree1.left  # Node found in common_nodes and has only a left child

        # Node found in common_nodes and has both left and right children
        # Replace the node with the maximum node in the left subtree
        max_left = find_max(tree1.left)
        tree1.value = max_left.value
        # Remove the maximum node from the left subtree
        tree1.left = remove_nodes_array(tree1.left, {max_left.value})

    # Update the height and balance factor
    update_height(tree1)
    tree1.balance_factor = balance_factor(tree1)

    return tree1

#! Stop


def remove_common_nodes_dict(tree1, tree2, key):
    """
    Removes nodes from tree1 that are present in tree2 based on the specified key.

    :param tree1: The root node of the first AVL tree.
    :type tree1: TreeNode or None
    :param tree2: The root node of the second AVL tree.
    :type tree2: TreeNode or None
    :param key: The key based on which nodes are compared and removed.
    :type key: str
    :return: The modified root node of tree1.
    :rtype: TreeNode or None
    """
    if tree1 is None:
        return None

    # Traverse the entire tree and identify common nodes
    common_nodes = find_common_nodes_dict(tree1, tree2, key, set())

    # Remove common nodes in a bottom-up manner
    return remove_nodes_dict(tree1, common_nodes, key)


def find_common_nodes_dict(tree1, tree2, key, common_nodes):
    """
    Helper function to find common nodes in tree1 and tree2.

    :param tree1: The root node of the first AVL tree.
    :type tree1: TreeNode or None
    :param tree2: The root node of the second AVL tree.
    :type tree2: TreeNode or None
    :param key: The key based on which nodes are compared.
    :type key: str
    :param common_nodes: Set to store common nodes.
    :type common_nodes: set
    :return: Set of common nodes.
    :rtype: set
    """
    if tree1 is not None:
        # Check if the current node is present in tree2
        if search_in_avl_tree_dict(tree2, key, tree1.value.get(key)):
            common_nodes.add(tree1.value.get(key))

        # Traverse left and right subtrees
        find_common_nodes_dict(tree1.left, tree2, key, common_nodes)
        find_common_nodes_dict(tree1.right, tree2, key, common_nodes)

    return common_nodes


def remove_nodes_dict(tree1, common_nodes, key):
    """
    Helper function to remove common nodes from tree1.

    :param tree1: The root node of the first AVL tree.
    :type tree1: TreeNode or None
    :param common_nodes: Set of common nodes.
    :type common_nodes: set
    :param key: The key based on which nodes are removed.
    :type key: str
    :return: The modified root node of tree1.
    :rtype: TreeNode or None
    """
    if tree1 is None:
        return None

    # Remove nodes in the left subtree
    tree1.left = remove_nodes_dict(tree1.left, common_nodes, key)

    # Remove nodes in the right subtree
    tree1.right = remove_nodes_dict(tree1.right, common_nodes, key)

    # Check if the current node is present in common_nodes
    if tree1.value.get(key) in common_nodes:
        if tree1.left is None and tree1.right is None:
            return None  # Node found in common_nodes and has no children, remove it from tree1
        elif tree1.left is None:
            return tree1.right  # Node found in common_nodes and has only a right child
        elif tree1.right is None:
            return tree1.left  # Node found in common_nodes and has only a left child

        # Node found in common_nodes and has both left and right children
        # Replace the node with the maximum node in the left subtree
        max_left = find_max(tree1.left)
        tree1.value = max_left.value
        # Remove the node that was moved
        tree1.left = remove_nodes_dict(tree1.left, common_nodes, key)
        return tree1

    # Update the height and balance factor
    update_height(tree1)
    tree1.balance_factor = balance_factor(tree1)

    return tree1


def find_max(node):
    """
    Find the maximum node in the AVL tree.

    :param node: The root node of the AVL tree.
    :type node: TreeNode or None
    :return: The maximum node.
    :rtype: TreeNode or None
    """
    while node.right:
        node = node.right
    return node


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
