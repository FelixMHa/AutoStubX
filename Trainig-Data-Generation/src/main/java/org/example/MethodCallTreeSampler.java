package org.example;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.*;

public class MethodCallTreeSampler {

    private static final List<String> MUTATOR_PREFIXES = List.of(
            "add", "put", "insert", "append", "push", "offer", "set", "remove", "clear"
    );

    private final Class<?> clazz;
    private final Random random = new Random();

    public MethodCallTreeSampler(Class<?> clazz) {
        this.clazz = clazz;
    }

    public static class TreeNode {
        public Method method;
        public Object[] args;
        public List<TreeNode> children = new ArrayList<>();

        public TreeNode(Method method, Object[] args) {
            this.method = method;
            this.args = args;
        }

        public String toCode() {
            StringBuilder sb = new StringBuilder(method.getName() + "(");
            for (int i = 0; i < args.length; i++) {
                sb.append("\"").append(args[i]).append("\"");
                if (i < args.length - 1) sb.append(", ");
            }
            sb.append(")");
            return sb.toString();
        }
    }

    public TreeNode buildMethodTree(Object baseObject, int maxDepth) {
        TreeNode root = new TreeNode(null, new Object[0]); // virtual root
        buildRecursive(baseObject, root, maxDepth);
        return root;
    }

    private void buildRecursive(Object baseObject, TreeNode parent, int depth) {
        if (depth <= 0 || baseObject == null) return;

        Method[] methods = clazz.getDeclaredMethods();

        for (Method method : methods) {
            if (!Modifier.isPublic(method.getModifiers())) continue;
            if (!MUTATOR_PREFIXES.stream().anyMatch(method.getName()::startsWith)) continue;
            if (method.getParameterCount() > 2) continue;

            try {
                Object[] args = RandomDataProvider.generateRandomArgs(method);
                method.invoke(baseObject, args);

                TreeNode child = new TreeNode(method, args);
                parent.children.add(child);

                // recurse with updated state
                buildRecursive(baseObject, child, depth - 1);

            } catch (Exception ignored) {
            }
        }
    }

    public List<String> samplePathToTarget(TreeNode root, Method target, Object baseObject) {
        List<TreeNode> path = new ArrayList<>();
        if (dfsFindPath(root, target, baseObject, path)) {
            List<String> calls = new ArrayList<>();
            for (TreeNode node : path) {
                if (node.method != null)
                    calls.add(node.toCode());
            }
            return calls;
        }
        return null;
    }

    private boolean dfsFindPath(TreeNode node, Method target, Object baseObject, List<TreeNode> path) {
        path.add(node);
        try {
            Object[] args = RandomDataProvider.generateRandomArgs(target);
            target.invoke(baseObject, args);
            path.add(new TreeNode(target, args));
            return true;
        } catch (Exception e) {
            // Try children
            for (TreeNode child : node.children) {
                if (dfsFindPath(child, target, baseObject, path)) return true;
            }
        }
        path.remove(path.size() - 1);
        return false;
    }
}
