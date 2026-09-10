from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
import os
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

from rungp import loadtrainingdata


INT = {"byte", "short", "int", "long", "b", "s", "i", "j"}
REAL = {"float", "double", "f", "d"}
BOOL = {"boolean", "bool", "z"}
CHAR = {"char", "c"}
VOID = {"void", "v", "java.lang.void", ""}
ERROR = {"error", "exception", "throw", "thrown"}
BOXED_INT = {"java.lang.byte", "java.lang.short", "java.lang.integer", "java.lang.long"}
BOXED_REAL = {"java.lang.float", "java.lang.double"}
BOXED_BOOL = {"java.lang.boolean"}
BOXED_CHAR = {"java.lang.character"}
BOXED = BOXED_INT | BOXED_REAL | BOXED_BOOL | BOXED_CHAR
STRING = {"java.lang.string", "string", "str", "charsequence", "java.lang.charsequence"}
OBJECT = {"object", "java.lang.object", "any", "value", "jvalue"}


class UnsupportedConcreteValue(ValueError):
    """A concrete training value cannot be represented by this SMT model."""


class JdkReplayError(RuntimeError):
    """The concrete sequence could not be replayed faithfully on the selected JDK."""


JDK_REPLAY_SOURCE = r"""
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public final class PushGpJdkReplay {
    static final class MiniJson {
        static Object parse(String s) {
            return new Parser(s).parse();
        }

        static String stringify(Object x) {
            StringBuilder b = new StringBuilder();
            write(b, x);
            return b.toString();
        }

        static void write(StringBuilder b, Object x) {
            if (x == null) { b.append("null"); return; }
            if (x instanceof Boolean || x instanceof Number) { b.append(x.toString()); return; }
            if (x instanceof String) { quote(b, (String)x); return; }
            if (x instanceof Map<?,?> m) {
                b.append('{');
                boolean first = true;
                for (Map.Entry<?,?> e : m.entrySet()) {
                    if (!first) b.append(',');
                    first = false;
                    quote(b, String.valueOf(e.getKey()));
                    b.append(':');
                    write(b, e.getValue());
                }
                b.append('}');
                return;
            }
            if (x instanceof Iterable<?> it) {
                b.append('[');
                boolean first = true;
                for (Object v : it) {
                    if (!first) b.append(',');
                    first = false;
                    write(b, v);
                }
                b.append(']');
                return;
            }
            if (x.getClass().isArray()) {
                b.append('[');
                int n = Array.getLength(x);
                for (int i = 0; i < n; i++) {
                    if (i != 0) b.append(',');
                    write(b, Array.get(x, i));
                }
                b.append(']');
                return;
            }
            quote(b, String.valueOf(x));
        }

        static void quote(StringBuilder b, String s) {
            b.append('"');
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"' -> b.append("\\\"");
                    case '\\' -> b.append("\\\\");
                    case '\b' -> b.append("\\b");
                    case '\f' -> b.append("\\f");
                    case '\n' -> b.append("\\n");
                    case '\r' -> b.append("\\r");
                    case '\t' -> b.append("\\t");
                    default -> {
                        if (c < 0x20) b.append(String.format("\\u%04x", (int)c));
                        else b.append(c);
                    }
                }
            }
            b.append('"');
        }

        static final class Parser {
            final String s;
            int p;
            Parser(String s) { this.s = s; }
            Object parse() {
                ws();
                Object v = value();
                ws();
                if (p != s.length()) throw new IllegalArgumentException("trailing JSON at " + p);
                return v;
            }
            Object value() {
                ws();
                if (p >= s.length()) throw new IllegalArgumentException("unexpected EOF");
                char c = s.charAt(p);
                if (c == '"') return string();
                if (c == '{') return object();
                if (c == '[') return array();
                if (s.startsWith("true", p)) { p += 4; return Boolean.TRUE; }
                if (s.startsWith("false", p)) { p += 5; return Boolean.FALSE; }
                if (s.startsWith("null", p)) { p += 4; return null; }
                return number();
            }
            Map<String,Object> object() {
                LinkedHashMap<String,Object> m = new LinkedHashMap<>();
                p++; ws();
                if (peek('}')) { p++; return m; }
                while (true) {
                    ws();
                    String k = string();
                    ws(); expect(':');
                    m.put(k, value());
                    ws();
                    if (peek('}')) { p++; return m; }
                    expect(',');
                }
            }
            List<Object> array() {
                ArrayList<Object> a = new ArrayList<>();
                p++; ws();
                if (peek(']')) { p++; return a; }
                while (true) {
                    a.add(value()); ws();
                    if (peek(']')) { p++; return a; }
                    expect(',');
                }
            }
            String string() {
                expect('"');
                StringBuilder b = new StringBuilder();
                while (p < s.length()) {
                    char c = s.charAt(p++);
                    if (c == '"') return b.toString();
                    if (c != '\\') { b.append(c); continue; }
                    if (p >= s.length()) throw new IllegalArgumentException("bad escape");
                    char e = s.charAt(p++);
                    switch (e) {
                        case '"' -> b.append('"');
                        case '\\' -> b.append('\\');
                        case '/' -> b.append('/');
                        case 'b' -> b.append('\b');
                        case 'f' -> b.append('\f');
                        case 'n' -> b.append('\n');
                        case 'r' -> b.append('\r');
                        case 't' -> b.append('\t');
                        case 'u' -> {
                            if (p + 4 > s.length()) throw new IllegalArgumentException("bad unicode escape");
                            b.append((char)Integer.parseInt(s.substring(p, p + 4), 16));
                            p += 4;
                        }
                        default -> throw new IllegalArgumentException("bad escape: " + e);
                    }
                }
                throw new IllegalArgumentException("unterminated string");
            }
            Number number() {
                int start = p;
                if (peek('-')) p++;
                while (p < s.length() && Character.isDigit(s.charAt(p))) p++;
                boolean real = false;
                if (peek('.')) { real = true; p++; while (p < s.length() && Character.isDigit(s.charAt(p))) p++; }
                if (p < s.length() && (s.charAt(p) == 'e' || s.charAt(p) == 'E')) {
                    real = true; p++;
                    if (p < s.length() && (s.charAt(p) == '+' || s.charAt(p) == '-')) p++;
                    while (p < s.length() && Character.isDigit(s.charAt(p))) p++;
                }
                String n = s.substring(start, p);
                if (real) return Double.valueOf(n);
                return Long.valueOf(n);
            }
            void ws() { while (p < s.length() && Character.isWhitespace(s.charAt(p))) p++; }
            boolean peek(char c) { return p < s.length() && s.charAt(p) == c; }
            void expect(char c) {
                ws();
                if (!peek(c)) throw new IllegalArgumentException("expected " + c + " at " + p);
                p++;
            }
        }
    }

    static String norm(String s) {
        if (s == null) return "";
        s = s.trim().replace('/', '.');
        if (s.startsWith("L") && s.endsWith(";")) s = s.substring(1, s.length() - 1);
        return s.toLowerCase(Locale.ROOT);
    }

    static Class<?> typeClass(String name) throws Exception {
        String n = norm(name);
        return switch (n) {
            case "byte", "b" -> byte.class;
            case "short", "s" -> short.class;
            case "int", "i" -> int.class;
            case "long", "j" -> long.class;
            case "float", "f" -> float.class;
            case "double", "d" -> double.class;
            case "boolean", "bool", "z" -> boolean.class;
            case "char", "c" -> char.class;
            case "void", "v", "" -> void.class;
            default -> {
                String raw = name == null ? "java.lang.Object" : name.trim().replace('/', '.');
                if (raw.startsWith("L") && raw.endsWith(";")) raw = raw.substring(1, raw.length() - 1);
                if (raw.startsWith("[")) yield Class.forName(raw.replace('/', '.'));
                if (raw.endsWith("[]")) yield Array.newInstance(typeClass(raw.substring(0, raw.length() - 2)), 0).getClass();
                yield Class.forName(raw);
            }
        };
    }

    static boolean isMapType(String t) { return norm(t).contains("map"); }
    static boolean isSetType(String t) { return norm(t).contains("set"); }
    static boolean isListType(String t) {
        String n = norm(t);
        return n.contains("list") || n.contains("collection") || n.contains("deque") || n.contains("queue") || n.contains("stack");
    }

    static Object newContainer(String typeName, int sizeHint) throws Exception {
        Class<?> cls;
        try { cls = typeClass(typeName); } catch (Throwable ignored) { cls = null; }
        if (cls != null && cls.isArray()) return Array.newInstance(cls.getComponentType(), sizeHint);
        if (cls != null && !cls.isInterface() && !Modifier.isAbstract(cls.getModifiers())) {
            try {
                Constructor<?> c = cls.getDeclaredConstructor();
                try { c.setAccessible(true); } catch (Throwable ignored) {}
                return c.newInstance();
            } catch (Throwable ignored) {}
        }
        String n = norm(typeName);
        if (n.contains("sortedmap") || n.contains("navigablemap") || n.contains("treemap")) return new TreeMap<>();
        if (n.contains("map")) return new LinkedHashMap<>();
        if (n.contains("sortedset") || n.contains("navigableset") || n.contains("treeset")) return new TreeSet<>();
        if (n.contains("set")) return new LinkedHashSet<>();
        if (n.contains("deque") || n.contains("queue")) return new ArrayDeque<>();
        if (n.contains("stack")) return new Stack<>();
        return new ArrayList<>();
    }

    @SuppressWarnings("unchecked")
    static Object decodeWire(Object wire, String typeHint, Map<Integer,Object> refs, IdentityHashMap<Object,Integer> ids) throws Exception {
        if (wire == null) return null;
        if (wire instanceof Map<?,?> mm) {
            Map<String,Object> m = (Map<String,Object>)mm;
            String kind = String.valueOf(m.getOrDefault("kind", ""));
            if (kind.equals("reference")) {
                int id = ((Number)m.get("id")).intValue();
                if (!refs.containsKey(id)) throw new IllegalStateException("reference " + id + " is not live on the JDK heap");
                return refs.get(id);
            }
            if (kind.equals("float-special")) {
                String v = String.valueOf(m.get("value"));
                double d = v.equals("NaN") ? Double.NaN : (v.equals("Infinity") ? Double.POSITIVE_INFINITY : Double.NEGATIVE_INFINITY);
                return norm(typeHint).equals("float") || norm(typeHint).equals("f") || norm(typeHint).equals("java.lang.float") ? (float)d : d;
            }
            if (kind.equals("map")) {
                Object out = newContainer(typeHint == null ? "java.util.LinkedHashMap" : typeHint, 0);
                if (!(out instanceof Map<?,?>)) out = new LinkedHashMap<>();
                Map<Object,Object> map = (Map<Object,Object>)out;
                for (Object e0 : (List<Object>)m.getOrDefault("entries", List.of())) {
                    List<Object> e = (List<Object>)e0;
                    map.put(decodeWire(e.get(0), "java.lang.Object", refs, ids), decodeWire(e.get(1), "java.lang.Object", refs, ids));
                }
                return map;
            }
            if (kind.equals("set")) {
                Object out = newContainer(typeHint == null ? "java.util.LinkedHashSet" : typeHint, 0);
                if (!(out instanceof Set<?>)) out = new LinkedHashSet<>();
                Set<Object> set = (Set<Object>)out;
                for (Object v : (List<Object>)m.getOrDefault("values", List.of())) set.add(decodeWire(v, "java.lang.Object", refs, ids));
                return set;
            }
        }
        if (wire instanceof List<?> list) {
            Class<?> target = null;
            try { target = typeClass(typeHint); } catch (Throwable ignored) {}
            if (target != null && target.isArray()) {
                Object arr = Array.newInstance(target.getComponentType(), list.size());
                for (int i = 0; i < list.size(); i++) Array.set(arr, i, coerce(decodeWire(list.get(i), target.getComponentType().getName(), refs, ids), target.getComponentType()));
                return arr;
            }
            Object out = newContainer(typeHint == null ? "java.util.ArrayList" : typeHint, list.size());
            if (out instanceof Collection<?> cc) {
                Collection<Object> c = (Collection<Object>)cc;
                for (Object v : list) c.add(decodeWire(v, "java.lang.Object", refs, ids));
                return c;
            }
        }
        Class<?> target = null;
        try { target = typeClass(typeHint); } catch (Throwable ignored) {}
        return target == null ? wire : coerce(wire, target);
    }

    static Object coerce(Object x, Class<?> t) {
        if (x == null) return null;
        if (t.isInstance(x)) return x;
        if (t == Object.class) return x;
        if (t == String.class || t == CharSequence.class) return String.valueOf(x);
        if (t == char.class || t == Character.class) {
            String s = String.valueOf(x);
            return s.isEmpty() ? '\0' : s.charAt(0);
        }
        if (t == boolean.class || t == Boolean.class) {
            if (x instanceof Boolean) return x;
            return Boolean.parseBoolean(String.valueOf(x));
        }
        if (x instanceof Number n) {
            if (t == byte.class || t == Byte.class) return n.byteValue();
            if (t == short.class || t == Short.class) return n.shortValue();
            if (t == int.class || t == Integer.class) return n.intValue();
            if (t == long.class || t == Long.class) return n.longValue();
            if (t == float.class || t == Float.class) return n.floatValue();
            if (t == double.class || t == Double.class) return n.doubleValue();
        }
        if (t.isEnum()) {
            @SuppressWarnings({"rawtypes", "unchecked"}) Object e = Enum.valueOf((Class<? extends Enum>)t, String.valueOf(x));
            return e;
        }
        return x;
    }

    static Object constructObject(String typeName, Object data, Map<Integer,Object> refs, IdentityHashMap<Object,Integer> ids) throws Exception {
        String n = norm(typeName);
        if (isMapType(typeName) || isSetType(typeName) || isListType(typeName) || (data instanceof List<?>) || (data instanceof Map<?,?> && !((Map<?,?>)data).containsKey("kind"))) {
            return decodeWire(data, typeName, refs, ids);
        }
        if (n.equals("java.lang.string") || n.equals("string")) return data == null ? null : String.valueOf(data);
        Class<?> cls;
        try { cls = typeClass(typeName); } catch (Throwable ex) { return data; }
        if (cls.isPrimitive() || Number.class.isAssignableFrom(cls) || cls == Boolean.class || cls == Character.class || cls == String.class || cls == Object.class) {
            return coerce(data, cls);
        }
        if (cls == StringBuilder.class) return new StringBuilder(data == null ? "" : String.valueOf(data));
        if (cls == StringBuffer.class) return new StringBuffer(data == null ? "" : String.valueOf(data));
        if (data != null) {
            for (Constructor<?> c : cls.getDeclaredConstructors()) {
                if (c.getParameterCount() != 1) continue;
                try {
                    Object arg = coerce(data, c.getParameterTypes()[0]);
                    try { c.setAccessible(true); } catch (Throwable ignored) {}
                    return c.newInstance(arg);
                } catch (Throwable ignored) {}
            }
        }
        Constructor<?> c = cls.getDeclaredConstructor();
        try { c.setAccessible(true); } catch (Throwable ignored) {}
        return c.newInstance();
    }

    @SuppressWarnings("unchecked")
    static void fillContainer(Object obj, Object wire, String typeName, Map<Integer,Object> refs, IdentityHashMap<Object,Integer> ids) throws Exception {
        if (obj == null) return;
        if (obj.getClass().isArray() && wire instanceof List<?> list) {
            Class<?> ct = obj.getClass().getComponentType();
            for (int i = 0; i < Math.min(list.size(), Array.getLength(obj)); i++) Array.set(obj, i, coerce(decodeWire(list.get(i), ct.getName(), refs, ids), ct));
            return;
        }
        if (obj instanceof List<?> ll && wire instanceof List<?> list) {
            List<Object> out = (List<Object>)ll;
            out.clear();
            for (Object v : list) out.add(decodeWire(v, "java.lang.Object", refs, ids));
            return;
        }
        if (obj instanceof Set<?> ss && wire instanceof Map<?,?> mm && "set".equals(String.valueOf(mm.get("kind")))) {
            Set<Object> out = (Set<Object>)ss;
            out.clear();
            for (Object v : (List<Object>)(mm.containsKey("values") ? mm.get("values") : List.of())) out.add(decodeWire(v, "java.lang.Object", refs, ids));
            return;
        }
        if (obj instanceof Map<?,?> map0 && wire instanceof Map<?,?> mm && "map".equals(String.valueOf(mm.get("kind")))) {
            Map<Object,Object> out = (Map<Object,Object>)map0;
            out.clear();
            for (Object e0 : (List<Object>)(mm.containsKey("entries") ? mm.get("entries") : List.of())) {
                List<Object> e = (List<Object>)e0;
                out.put(decodeWire(e.get(0), "java.lang.Object", refs, ids), decodeWire(e.get(1), "java.lang.Object", refs, ids));
            }
        }
    }

    static Method resolveMethod(Class<?> owner, String name, Class<?>[] declared, Object[] args) throws Exception {
        try { return owner.getMethod(name, declared); } catch (NoSuchMethodException ignored) {}
        for (Method m : owner.getMethods()) {
            if (!m.getName().equals(name) || m.getParameterCount() != declared.length) continue;
            Class<?>[] ps = m.getParameterTypes();
            boolean ok = true;
            for (int i = 0; i < ps.length; i++) {
                if (args[i] == null) { if (ps[i].isPrimitive()) ok = false; }
                else if (!box(ps[i]).isAssignableFrom(box(args[i].getClass()))) ok = false;
                if (!ok) break;
            }
            if (ok) return m;
        }
        throw new NoSuchMethodException(owner.getName() + "." + name + Arrays.toString(declared));
    }

    static Class<?> box(Class<?> c) {
        if (!c.isPrimitive()) return c;
        if (c == byte.class) return Byte.class;
        if (c == short.class) return Short.class;
        if (c == int.class) return Integer.class;
        if (c == long.class) return Long.class;
        if (c == float.class) return Float.class;
        if (c == double.class) return Double.class;
        if (c == boolean.class) return Boolean.class;
        if (c == char.class) return Character.class;
        return c;
    }

    static boolean valueLike(Object x) {
        return x == null || x instanceof String || x instanceof Number || x instanceof Boolean || x instanceof Character || x.getClass().isEnum();
    }

    static Object encodeValue(Object x, String declaredType, Map<Integer,Object> refs, IdentityHashMap<Object,Integer> ids, int[] nextRef) {
        if (x == null) return null;
        if (x instanceof Double d && !Double.isFinite(d)) return Map.of("kind", "float-special", "value", Double.isNaN(d) ? "NaN" : (d > 0 ? "Infinity" : "-Infinity"));
        if (x instanceof Float f && !Float.isFinite(f)) return Map.of("kind", "float-special", "value", Float.isNaN(f) ? "NaN" : (f > 0 ? "Infinity" : "-Infinity"));
        if (x instanceof Character c) return String.valueOf(c);
        if (x.getClass().isEnum()) return ((Enum<?>)x).name();
        if (valueLike(x)) return x;
        Integer id = ids.get(x);
        if (id == null) {
            id = nextRef[0]++;
            ids.put(x, id);
            refs.put(id, x);
        }
        LinkedHashMap<String,Object> r = new LinkedHashMap<>();
        r.put("kind", "reference");
        r.put("id", id);
        return r;
    }

    static Object encodeStateObject(Object x, Map<Integer,Object> refs, IdentityHashMap<Object,Integer> ids, int[] nextRef) {
        if (x == null || valueLike(x)) return encodeValue(x, "java.lang.Object", refs, ids, nextRef);
        if (x.getClass().isArray()) {
            ArrayList<Object> a = new ArrayList<>();
            for (int i = 0; i < Array.getLength(x); i++) a.add(encodeValue(Array.get(x, i), "java.lang.Object", refs, ids, nextRef));
            return a;
        }
        if (x instanceof List<?> l) {
            ArrayList<Object> a = new ArrayList<>();
            for (Object v : l) a.add(encodeValue(v, "java.lang.Object", refs, ids, nextRef));
            return a;
        }
        if (x instanceof Set<?> s) {
            ArrayList<Object> a = new ArrayList<>();
            for (Object v : s) a.add(encodeValue(v, "java.lang.Object", refs, ids, nextRef));
            LinkedHashMap<String,Object> m = new LinkedHashMap<>(); m.put("kind", "set"); m.put("values", a); return m;
        }
        if (x instanceof Map<?,?> map) {
            ArrayList<Object> es = new ArrayList<>();
            for (Map.Entry<?,?> e : map.entrySet()) es.add(List.of(encodeValue(e.getKey(), "java.lang.Object", refs, ids, nextRef), encodeValue(e.getValue(), "java.lang.Object", refs, ids, nextRef)));
            LinkedHashMap<String,Object> m = new LinkedHashMap<>(); m.put("kind", "map"); m.put("entries", es); return m;
        }
        return Map.of("kind", "object", "class", x.getClass().getName(), "text", String.valueOf(x));
    }

    @SuppressWarnings("unchecked")
    static Map<String,Object> replay(Map<String,Object> req) throws Exception {
        HashMap<Integer,Object> refs = new HashMap<>();
        IdentityHashMap<Object,Integer> ids = new IdentityHashMap<>();
        int[] nextRef = { ((Number)req.getOrDefault("nextRef", 0L)).intValue() };
        List<Object> initial = (List<Object>)req.getOrDefault("initial", List.of());

        // First pass creates stable identities for all initial references.
        for (Object e0 : initial) {
            Map<String,Object> e = (Map<String,Object>)e0;
            int id = ((Number)e.get("id")).intValue();
            String type = String.valueOf(e.getOrDefault("type", "java.lang.Object"));
            Object data = e.get("data");
            Object obj;
            Class<?> tc = null;
            try { tc = typeClass(type); } catch (Throwable ignored) {}
            if (tc != null && tc.isArray() && data instanceof List<?> l) obj = Array.newInstance(tc.getComponentType(), l.size());
            else if (isMapType(type)) obj = newContainer(type, 0);
            else if (isSetType(type)) obj = newContainer(type, 0);
            else if (isListType(type) || data instanceof List<?>) obj = newContainer(type, data instanceof List<?> l ? l.size() : 0);
            else obj = constructObject(type, data, refs, ids);
            refs.put(id, obj);
            if (obj != null && !valueLike(obj)) ids.put(obj, id);
        }
        // Second pass fills containers after every initial identity exists.
        for (Object e0 : initial) {
            Map<String,Object> e = (Map<String,Object>)e0;
            int id = ((Number)e.get("id")).intValue();
            fillContainer(refs.get(id), e.get("data"), String.valueOf(e.getOrDefault("type", "java.lang.Object")), refs, ids);
        }

        ArrayList<Object> results = new ArrayList<>();
        for (Object c0 : (List<Object>)req.getOrDefault("calls", List.of())) {
            Map<String,Object> c = (Map<String,Object>)c0;
            String ownerName = String.valueOf(c.get("owner"));
            String methodName = String.valueOf(c.get("name"));
            boolean isStatic = Boolean.TRUE.equals(c.get("isStatic"));
            List<Object> typeNames = (List<Object>)c.getOrDefault("argumentTypes", List.of());
            List<Object> argWires = (List<Object>)c.getOrDefault("args", List.of());
            Class<?>[] ptypes = new Class<?>[typeNames.size()];
            Object[] args = new Object[typeNames.size()];
            for (int i = 0; i < ptypes.length; i++) {
                String tn = String.valueOf(typeNames.get(i));
                ptypes[i] = typeClass(tn);
                Object w = argWires.get(i);
                if (w instanceof Map<?,?> wm && "fresh".equals(String.valueOf(wm.get("kind")))) {
                    int id = ((Number)wm.get("id")).intValue();
                    Object obj = decodeWire(wm.get("value"), tn, refs, ids);
                    refs.put(id, obj);
                    if (obj != null && !valueLike(obj)) ids.put(obj, id);
                    args[i] = coerce(obj, ptypes[i]);
                } else {
                    args[i] = coerce(decodeWire(w, tn, refs, ids), ptypes[i]);
                }
            }
            Object receiver = null;
            if (!isStatic) {
                int rid = ((Number)c.get("receiver")).intValue();
                if (!refs.containsKey(rid)) throw new IllegalStateException("receiver reference " + rid + " is not live on the JDK heap");
                receiver = refs.get(rid);
            }

            LinkedHashMap<String,Object> out = new LinkedHashMap<>();
            try {
                Class<?> owner = typeClass(ownerName);
                Method m = resolveMethod(owner, methodName, ptypes, args);
                try { m.setAccessible(true); } catch (Throwable ignored) {}
                Object value = m.invoke(receiver, args);
                Object bind0 = c.get("bindReturnRef");
                if (bind0 instanceof Number && value != null && !valueLike(value)) {
                    int bind = ((Number)bind0).intValue();
                    refs.put(bind, value);
                    ids.put(value, bind);
                    if (bind >= nextRef[0]) nextRef[0] = bind + 1;
                }
                out.put("outcome", "normal");
                out.put("value", encodeValue(value, String.valueOf(c.getOrDefault("returnType", "java.lang.Object")), refs, ids, nextRef));
            } catch (InvocationTargetException ex) {
                Throwable t = ex.getTargetException();
                out.put("outcome", "thrown");
                out.put("exceptionType", t.getClass().getName());
                out.put("message", t.getMessage());
            }
            if (!isStatic) {
                int rid = ((Number)c.get("receiver")).intValue();
                out.put("receiverState", encodeStateObject(refs.get(rid), refs, ids, nextRef));
            }
            results.add(out);
        }
        LinkedHashMap<String,Object> ans = new LinkedHashMap<>();
        ans.put("results", results);
        ans.put("nextRef", nextRef[0]);
        return ans;
    }

    public static void main(String[] args) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, java.nio.charset.StandardCharsets.UTF_8));
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, java.nio.charset.StandardCharsets.UTF_8));
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) continue;
            LinkedHashMap<String,Object> response = new LinkedHashMap<>();
            try {
                @SuppressWarnings("unchecked") Map<String,Object> req = (Map<String,Object>)MiniJson.parse(line);
                response.putAll(replay(req));
            } catch (Throwable t) {
                response.put("fatal", t.getClass().getName() + ": " + String.valueOf(t.getMessage()));
                StringWriter sw = new StringWriter();
                t.printStackTrace(new PrintWriter(sw));
                response.put("stack", sw.toString());
            }
            out.write(MiniJson.stringify(response));
            out.newLine();
            out.flush();
        }
    }
}
"""


def _wire_value(x: Any) -> Any:
    """Convert a training value to a JSON-safe value without losing map key types."""
    ref = ref_value(x)
    if ref is not None:
        return {"kind": "reference", "id": ref}
    if x is None or isinstance(x, (str, bool, int)):
        return x
    if isinstance(x, float):
        if math.isnan(x):
            return {"kind": "float-special", "value": "NaN"}
        if math.isinf(x):
            return {"kind": "float-special", "value": "Infinity" if x > 0 else "-Infinity"}
        return x
    if isinstance(x, (list, tuple)):
        return [_wire_value(v) for v in x]
    if isinstance(x, set):
        return {"kind": "set", "values": [_wire_value(v) for v in x]}
    if isinstance(x, dict):
        return {"kind": "map", "entries": [[_wire_value(k), _wire_value(v)] for k, v in x.items()]}
    raise JdkReplayError(f"Cannot replay value of type {type(x).__name__}: {x!r}")


def _java_method_name(
    method_key: str,
    info: dict[str, Any],
) -> str:
    """
    Convert the PushGP/manifest method identifier into the actual JDK method name.
    """

    # Prefer explicit reflection metadata when available.
    for key in ("javaMethod", "methodName", "name", "jdkMethod"):
        value = info.get(key)
        if value:
            return str(value).strip()

    s = str(method_key).strip()

    # Strip Java-style signature if present:
    # get(int) -> get
    if "(" in s:
        s = s.split("(", 1)[0]

    # IMPORTANT:
    # '#' is an overload/signature suffix in your training method IDs.
    #
    # add#obj -> add
    # size#0  -> size
    #
    # Do NOT use rsplit(...)[-1].
    if "#" in s:
        s = s.split("#", 1)[0]

    # Strip optional owner prefix.
    #
    # java.util.ArrayList::add -> add
    if "::" in s:
        s = s.rsplit("::", 1)[-1]

    # java.util.ArrayList.add -> add
    if "." in s:
        s = s.rsplit(".", 1)[-1]

    if not s:
        raise JdkReplayError(
            f"Could not derive Java method name from {method_key!r}"
        )

    return s


def _jdk_receiver_type_hints(example: Any, methods: dict[str, dict]) -> dict[int, str]:
    """Choose concrete JVM receiver classes independently from the SMT heap ABI.

    The SMT intentionally collapses collections to list/map/set kinds.  A real
    replay must keep the actual declaring class when possible (for example
    LinkedList must not silently become ArrayList).
    """
    hints: dict[int, str] = {}
    receiver_refs = list(getattr(example, "receiver_refs", None) or [])
    generic_owners = {
        "java.util.collection", "java.util.list", "java.util.map", "java.util.set",
        "java.util.queue", "java.util.deque", "java.lang.object",
    }
    for i, method_name in enumerate(list(example.sequence or [])):
        info = methods.get(method_name)
        if not info or info.get("isStatic", False):
            continue
        ref = int(receiver_refs[i] if i < len(receiver_refs) else 0)
        owner = str(info.get("owner") or info.get("declaringClass") or "").strip()
        if not owner:
            continue
        previous = hints.get(ref)
        if previous is None or (norm(previous) in generic_owners and norm(owner) not in generic_owners):
            hints[ref] = owner
    return hints


def _generic_jdk_state_type(type_name: Any) -> bool:
    n = norm(type_name)
    return n in {
        "", "object", "java.lang.object", "reference", "ref",
        "list", "map", "set", "collection", "queue", "deque", "stack",
    }


def _jdk_payload(example: Any, methods: dict[str, dict]) -> dict[str, Any]:
    state = dict(example.initial_state or {})
    if not state:
        state = {0: []}
    default_type = str(example.data_structure_type or "object")
    receiver_hints = _jdk_receiver_type_hints(example, methods)
    initial = []
    for raw_ref, raw in state.items():
        ref = int(raw_ref)
        type_name, data = unpack_object(raw, default_type)
        # Raw list/map/set traces often erase the concrete container class. For
        # JDK replay, restore it from data_structure_type or the manifest owner.
        if _generic_jdk_state_type(type_name) and not _generic_jdk_state_type(default_type):
            type_name = default_type
        if _generic_jdk_state_type(type_name) and ref in receiver_hints:
            type_name = receiver_hints[ref]
        initial.append({"id": ref, "type": type_name, "data": _wire_value(data)})

    next_ref = max((int(r) for r in state), default=-1) + 1
    calls_out = []
    for i, method_key in enumerate(example.sequence):
        if method_key not in methods:
            raise JdkReplayError(f"Method {method_key!r} is not present in the SMT manifest")
        info = methods[method_key]
        owner = str(info.get("owner") or info.get("declaringClass") or "").strip()
        if not owner:
            raise JdkReplayError(f"Manifest method {method_key!r} has no owner/declaringClass for JDK replay")
        args = example.input_args[i]
        declared = list(info.get("argumentTypes", []))
        trace_types = example.type_inputs[i] if i < len(example.type_inputs) else []
        wire_args = []
        full_types = []
        for j, x in enumerate(args):
            t = declared[j] if j < len(declared) else (trace_types[j] if j < len(trace_types) else "java.lang.Object")
            full_types.append(str(t))
            c = collection_arg(x, t)
            if c:
                wire_args.append({"kind": "fresh", "id": next_ref, "value": _wire_value(x)})
                next_ref += 1
            else:
                wire_args.append(_wire_value(x))
        bind = ref_value(example.expected_outputs[i]) if i < len(example.expected_outputs) else None
        call = {
            "owner": owner,
            "name": _java_method_name(method_key, info),
            "isStatic": bool(info.get("isStatic", False)),
            "argumentTypes": full_types,
            "args": wire_args,
            "returnType": str(info.get("returnType") or "void"),
        }
        #print(
        #    f"JDK replay: {method_key!r} -> "
        #    f"{owner}.{call['name']}({', '.join(full_types)})"
        #)
        if not call["isStatic"]:
            call["receiver"] = int(example.receiver_refs[i] if i < len(example.receiver_refs) else 0)
        if bind is not None:
            # The trace's reference number is used only to preserve alias identity
            # for later calls. The concrete JDK value is still the oracle.
            call["bindReturnRef"] = bind
            if bind >= next_ref:
                next_ref = bind + 1
        calls_out.append(call)
    return {"initial": initial, "calls": calls_out, "nextRef": next_ref}


class JdkOracle:
    def __init__(self, java: str, javac: str, classpath: str):
        self._tmp = tempfile.TemporaryDirectory(prefix="pushgp_jdk_replay_")
        root = Path(self._tmp.name)
        source = root / "PushGpJdkReplay.java"
        source.write_text(JDK_REPLAY_SOURCE, encoding="utf-8")
        cp = classpath or "."
        compile_p = subprocess.run(
            [javac, "-encoding", "UTF-8", "-cp", cp, str(source)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        if compile_p.returncode:
            self._tmp.cleanup()
            raise JdkReplayError("Could not compile the JDK replay harness:\n" + compile_p.stdout + compile_p.stderr)
        run_cp = str(root) + os.pathsep + cp
        self._p = subprocess.Popen(
            [java, "-cp", run_cp, "PushGpJdkReplay"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="strict", bufsize=1,
        )

    def replay(self, example: Any, methods: dict[str, dict]) -> list[dict[str, Any]]:
        if self._p.poll() is not None:
            err = self._p.stderr.read() if self._p.stderr else ""
            raise JdkReplayError(f"JDK replay process exited early ({self._p.returncode}): {err}")
        assert self._p.stdin is not None and self._p.stdout is not None
        payload = _jdk_payload(example, methods)
        self._p.stdin.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._p.stdin.flush()
        line = self._p.stdout.readline()
        if not line:
            err = self._p.stderr.read() if self._p.stderr else ""
            raise JdkReplayError("JDK replay process produced no result. " + err)
        ans = json.loads(line)
        if ans.get("fatal"):
            raise JdkReplayError(ans["fatal"] + "\n" + ans.get("stack", ""))
        results = ans.get("results", [])
        if len(results) != len(example.sequence):
            raise JdkReplayError(f"JDK replay returned {len(results)} results for {len(example.sequence)} calls")
        return results

    def close(self) -> None:
        if getattr(self, "_p", None) is not None:
            try:
                if self._p.stdin:
                    self._p.stdin.close()
                self._p.terminate()
                self._p.wait(timeout=2)
            except Exception:
                self._p.kill()
        self._tmp.cleanup()

    def __enter__(self) -> "JdkOracle":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _oracle_value(x: Any) -> Any:
    if isinstance(x, dict) and x.get("kind") == "float-special":
        v = x.get("value")
        return float("nan") if v == "NaN" else (float("inf") if v == "Infinity" else float("-inf"))
    return x


def jdk_condition(result: str, jdk_result: dict[str, Any], declared_type: Any) -> str:
    if jdk_result.get("outcome") == "thrown":
        return f"(= (result-outcome {result}) OUT_THROWN)"
    if norm(declared_type) in VOID:
        return f"(and (= (result-outcome {result}) OUT_NORMAL) (= (result-exception {result}) EX_NONE))"
    value = _oracle_value(jdk_result.get("value"))
    return (
        f"(and (= (result-outcome {result}) OUT_NORMAL) "
        f"(= (result-exception {result}) EX_NONE) "
        f"(= (result-value {result}) {jvalue(value, declared_type)}))"
    )


def _jdk_state_atom(x: Any) -> Any:
    if isinstance(x, dict) and x.get("kind") == "float-special":
        return _oracle_value(x)
    if isinstance(x, dict) and x.get("kind") == "object":
        raise UnsupportedConcreteValue(
            f"Cannot structurally compare opaque JDK object state {x.get('class')!r}"
        )
    return x


def jdk_receiver_state_condition(
    result: str,
    receiver_ref: int,
    receiver_state: Any,
    receiver_type: Any,
) -> str | None:
    """Describe the concrete JDK receiver state in the SMT Heap schema.

    This is intentionally extensional for collections: size plus every concrete
    element/entry/member. Slots outside a list's size and absent map/set keys are
    irrelevant to the modeled Java state.
    """
    heap = f"(result-heap {result})"
    r = smt_int(receiver_ref)
    t = norm(receiver_type)

    if isinstance(receiver_state, list):
        parts = [
            f"(= (select (heap-kind {heap}) {r}) K_LIST)",
            f"(= (select (heap-list-size {heap}) {r}) {len(receiver_state)})",
        ]
        for i, value in enumerate(receiver_state):
            parts.append(
                f"(= (select (select (heap-list-data {heap}) {r}) {i}) "
                f"{jvalue(_jdk_state_atom(value))})"
            )
        return "(and " + " ".join(parts) + ")"

    if isinstance(receiver_state, dict) and receiver_state.get("kind") == "map":
        entries = list(receiver_state.get("entries", []))
        parts = [
            f"(= (select (heap-kind {heap}) {r}) K_MAP)",
            f"(= (select (heap-map-size {heap}) {r}) {len(entries)})",
        ]
        for key, value in entries:
            k = jvalue(_jdk_state_atom(key))
            v = jvalue(_jdk_state_atom(value))
            parts.append(f"(select (select (heap-map-present {heap}) {r}) {k})")
            parts.append(f"(= (select (select (heap-map-data {heap}) {r}) {k}) {v})")
        return "(and " + " ".join(parts) + ")"

    if isinstance(receiver_state, dict) and receiver_state.get("kind") == "set":
        values = list(receiver_state.get("values", []))
        parts = [
            f"(= (select (heap-kind {heap}) {r}) K_SET)",
            f"(= (select (heap-set-size {heap}) {r}) {len(values)})",
        ]
        for value in values:
            v = jvalue(_jdk_state_atom(value))
            parts.append(f"(select (select (heap-set-present {heap}) {r}) {v})")
        return "(and " + " ".join(parts) + ")"

    # Scalar-backed wrapper/String/object receivers use heap-object-value in the
    # generated ABI. If the Java snapshot is opaque, compare its textual payload
    # only when the manifest gives an explicit scalar receiverValueType.
    value = receiver_state
    if isinstance(receiver_state, dict) and receiver_state.get("kind") == "object":
        if t not in INT | REAL | BOOL | CHAR | BOXED | STRING:
            return None
        value = receiver_state.get("text")
    if t in INT | REAL | BOOL | CHAR | BOXED | STRING or not isinstance(value, (dict, list)):
        return (
            f"(and (= (select (heap-kind {heap}) {r}) K_OBJECT) "
            f"(= (select (heap-object-value {heap}) {r}) {jvalue(_jdk_state_atom(value), receiver_type)}))"
        )
    return None


def jdk_call_condition(
    result: str,
    jdk_result: dict[str, Any],
    declared_type: Any,
    receiver_ref: int | None,
    receiver_type: Any,
) -> tuple[str, bool]:
    result_cond = jdk_condition(result, jdk_result, declared_type)
    if receiver_ref is None or "receiverState" not in jdk_result:
        return result_cond, False
    try:
        state_cond = jdk_receiver_state_condition(
            result, receiver_ref, jdk_result["receiverState"], receiver_type
        )
    except UnsupportedConcreteValue:
        state_cond = None
    if not state_cond:
        return result_cond, False
    return f"(and {result_cond} {state_cond})", True


def _canonical_value(x: Any) -> Any:
    if isinstance(x, dict) and x.get("kind") == "float-special":
        return ("float-special", x.get("value"))
    ref = ref_value(x)
    if ref is not None:
        return ("ref", ref)
    if isinstance(x, float) and math.isnan(x):
        return ("float-special", "NaN")
    if isinstance(x, float) and math.isinf(x):
        return ("float-special", "Infinity" if x > 0 else "-Infinity")
    if isinstance(x, list):
        return tuple(_canonical_value(v) for v in x)
    return x


def training_agrees_with_jdk(jdk_result: dict[str, Any], expected: Any, trace_type: Any, declared_type: Any) -> bool:
    thrown = jdk_result.get("outcome") == "thrown"
    if thrown:
        return expected_error(expected, trace_type)
    if expected_error(expected, trace_type):
        return False
    if norm(declared_type) in VOID or norm(trace_type) in VOID:
        return True
    return _canonical_value(jdk_result.get("value")) == _canonical_value(expected)


def jdk_version(java: str) -> str:
    p = subprocess.run([java, "-version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
    text = (p.stderr or p.stdout).strip().splitlines()
    return text[0] if text else java


def norm(t: Any) -> str:
    s = "" if t is None else str(t).strip().replace("/", ".")
    return s[1:-1].lower() if s.startswith("L") and s.endswith(";") else s.lower()


def smt_int(x: Any) -> str:
    x = int(x)
    return str(x) if x >= 0 else f"(- {-x})"


def smt_real(x: Any) -> str:
    x = float(x)
    if not math.isfinite(x):
        # pushgp_smt models Java float/double values with SMT Real. SMT Real
        # has no NaN, +Infinity or -Infinity, so there is no faithful literal
        # we can emit for these training cases. Do not silently replace the
        # value with an arbitrary finite number; mark the case unsupported.
        raise UnsupportedConcreteValue(
            f"SMT Real cannot represent IEEE non-finite value {x!r}"
        )
    text = repr(x)
    if "e" in text.lower():
        f = Fraction(Decimal(text))
        n = smt_int(f.numerator)
        return n if f.denominator == 1 else f"(/ {n} {f.denominator})"
    if text.startswith("-"):
        return f"(- {text[1:]})"
    return text if "." in text else text + ".0"


def smt_str(x: Any) -> str:
    chunks, current = [], []

    def flush() -> None:
        if current:
            chunks.append('"' + "".join(current).replace('"', '""') + '"')
            current.clear()

    for ch in str(x):
        code = ord(ch)
        # Keep generated SMT text ASCII-safe.  This avoids Windows
        # console/code-page problems (for example U+0081 cannot be
        # encoded by cp1252) and is valid SMT-LIB string construction.
        if code < 0x20 or code > 0x7E:
            flush()
            chunks.append(f"(str.from_code {code})")
        else:
            current.append(ch)
    flush()
    if not chunks:
        return '""'
    return chunks[0] if len(chunks) == 1 else "(str.++ " + " ".join(chunks) + ")"


def is_reference_type(type_name: Any) -> bool:
    t = norm(type_name)
    if not t or t in INT | REAL | BOOL | CHAR | VOID | ERROR | BOXED | STRING | OBJECT | {"null", "none"}:
        return False
    if t in {"reference", "ref"} or t.startswith("[") or t.endswith("[]"):
        return True
    if any(k in t for k in ("list", "map", "set", "collection", "iterator")):
        return True
    # pushgp_smt treats other declared Java classes as heap references.
    return True


def ref_value(x: Any) -> int | None:
    if not isinstance(x, dict):
        return None
    if str(x.get("kind", "")).lower() not in {"reference", "ref", "object-reference"}:
        return None
    for key in ("id", "ref_id", "refId"):
        if key in x:
            return int(x[key])
    return None


def jvalue(x: Any, type_hint: Any = None) -> str:
    ref = ref_value(x)
    if ref is not None:
        return f"(JRef {smt_int(ref)})"

    t = norm(type_hint)
    if x is None:
        return "JNull"
    if t in INT or t in BOXED_INT:
        return f"(JInt {smt_int(x)})"
    if t in REAL or t in BOXED_REAL:
        return f"(JReal {smt_real(x)})"
    if t in BOOL or t in BOXED_BOOL:
        if isinstance(x, str):
            value = x.strip().lower() in {"true", "1", "yes"}
        else:
            value = bool(x)
        return f"(JBool {'true' if value else 'false'})"
    if t in CHAR or t in BOXED_CHAR:
        return f"(JString {smt_str(str(x)[:1])})"
    if is_reference_type(type_hint) and isinstance(x, int):
        return f"(JRef {smt_int(x)})"
    if isinstance(x, bool):
        return f"(JBool {'true' if x else 'false'})"
    if isinstance(x, int):
        return f"(JInt {smt_int(x)})"
    if isinstance(x, float):
        return f"(JReal {smt_real(x)})"
    if isinstance(x, str):
        return f"(JString {smt_str(x)})"
    raise ValueError(f"Cannot encode as JValue: {x!r}")


def argument(x: Any, type_name: Any) -> str:
    t = norm(type_name)
    if t in INT:
        return smt_int(x)
    if t in REAL:
        return smt_real(x)
    if t in BOOL:
        return "true" if bool(x) else "false"
    if t in CHAR:
        return smt_str(str(x)[:1])
    return jvalue(x, type_name)


def unpack_object(raw: Any, default_type: str) -> tuple[str, Any]:
    if isinstance(raw, dict) and "type" in raw and "data" in raw:
        return str(raw.get("type") or default_type), raw.get("data")
    if isinstance(raw, list) or isinstance(raw, tuple):
        return "list", list(raw)
    if isinstance(raw, set):
        return "set", raw
    if isinstance(raw, dict):
        return "map", raw
    return default_type, raw


def kind(type_name: str, data: Any) -> str:
    t = norm(type_name)
    if "map" in t or isinstance(data, dict):
        return "map"
    if "set" in t or isinstance(data, set):
        return "set"
    if any(k in t for k in ("list", "collection", "arraylist", "deque", "queue", "stack")) or isinstance(data, (list, tuple)):
        return "list"
    return "object"


def add_object(heap: str, ref: int, type_name: str, data: Any) -> str:
    """Encode one concrete heap object using the current pushgp_smt Heap schema.

    Heap now contains ``heap-object-value`` immediately after ``heap-kind``.
    Collection objects preserve that array unchanged; ordinary object/boxed-value
    receivers store their concrete payload in it.
    """
    r = smt_int(ref)
    k = kind(type_name, data)
    object_values = f"(heap-object-value {heap})"

    if k == "list":
        values = list(data or [])
        arr = "((as const (Array Int JValue)) JNull)"
        for i, v in enumerate(values):
            arr = f"(store {arr} {i} {jvalue(v)})"
        return (
            f"(mk-heap "
            f"(store (heap-kind {heap}) {r} K_LIST) "
            f"{object_values} "
            f"(store (heap-list-size {heap}) {r} {len(values)}) "
            f"(store (heap-list-data {heap}) {r} {arr}) "
            f"(heap-map-size {heap}) (heap-map-present {heap}) "
            f"(heap-map-data {heap}) (heap-set-size {heap}) "
            f"(heap-set-present {heap}))"
        )

    if k == "map":
        values = dict(data or {})
        present = "((as const (Array JValue Bool)) false)"
        arr = "((as const (Array JValue JValue)) JNull)"
        for key, value in values.items():
            key_smt = jvalue(key)
            present = f"(store {present} {key_smt} true)"
            arr = f"(store {arr} {key_smt} {jvalue(value)})"
        return (
            f"(mk-heap "
            f"(store (heap-kind {heap}) {r} K_MAP) "
            f"{object_values} "
            f"(heap-list-size {heap}) (heap-list-data {heap}) "
            f"(store (heap-map-size {heap}) {r} {len(values)}) "
            f"(store (heap-map-present {heap}) {r} {present}) "
            f"(store (heap-map-data {heap}) {r} {arr}) "
            f"(heap-set-size {heap}) (heap-set-present {heap}))"
        )

    if k == "set":
        values = list(data or [])
        present = "((as const (Array JValue Bool)) false)"
        for value in values:
            present = f"(store {present} {jvalue(value)} true)"
        return (
            f"(mk-heap "
            f"(store (heap-kind {heap}) {r} K_SET) "
            f"{object_values} "
            f"(heap-list-size {heap}) (heap-list-data {heap}) "
            f"(heap-map-size {heap}) (heap-map-present {heap}) "
            f"(heap-map-data {heap}) "
            f"(store (heap-set-size {heap}) {r} {len(values)}) "
            f"(store (heap-set-present {heap}) {r} {present}))"
        )

    payload = jvalue(data, type_name)
    return (
        f"(mk-heap "
        f"(store (heap-kind {heap}) {r} K_OBJECT) "
        f"(store (heap-object-value {heap}) {r} {payload}) "
        f"(heap-list-size {heap}) (heap-list-data {heap}) "
        f"(heap-map-size {heap}) (heap-map-present {heap}) "
        f"(heap-map-data {heap}) (heap-set-size {heap}) "
        f"(heap-set-present {heap}))"
    )


def _receiver_type_hints(example: Any, methods: dict[str, dict]) -> dict[int, str]:
    """Return authoritative receiver encoding hints from the SMT manifest.

    The trace's ``data_structure_type`` is a coarse/legacy default and can be
    wrong for scalar wrapper receivers.  The generated SMT stub, however, was
    compiled from exact method metadata.  Use the same owner/receiverKind when
    reconstructing the concrete pre-heap so tester and stub share one ABI.
    """
    hints: dict[int, str] = {}
    receiver_refs = list(getattr(example, "receiver_refs", None) or [])

    for i, method_name in enumerate(list(example.sequence or [])):
        info = methods.get(method_name)
        if not info or info.get("isStatic", False):
            continue

        ref = int(receiver_refs[i] if i < len(receiver_refs) else 0)
        owner = str(info.get("owner") or info.get("declaringClass") or "").strip()
        receiver_kind = str(info.get("receiverKind") or "generic").strip().lower()
        receiver_value_type = str(info.get("receiverValueType") or "").strip()

        # Prefer the exact payload type exported by pushgp_smt. This is the same
        # metadata used to generate the RECEIVER.VALUE selector/precondition.
        # Fall back to the declaring class for older manifests.
        owner_norm = norm(owner)
        if receiver_value_type:
            hint = receiver_value_type
        elif owner_norm in BOXED | STRING:
            hint = owner
        elif receiver_kind in {"list", "map", "set"}:
            hint = receiver_kind
        elif receiver_kind == "object":
            hint = owner or "object"
        else:
            hint = owner or receiver_kind or "object"

        previous = hints.get(ref)
        if previous is None:
            hints[ref] = hint
        elif kind(previous, None) != kind(hint, None):
            raise ValueError(
                f"Receiver {ref} has incompatible manifest kinds: {previous!r} vs {hint!r}"
            )

    return hints


def initial_heap(example: Any, methods: dict[str, dict]) -> tuple[str, int]:
    state = dict(example.initial_state or {})
    if not state:
        state = {0: []}
    default_type = str(example.data_structure_type or "object")
    receiver_hints = _receiver_type_hints(example, methods)
    lines = ["(define-fun h_init_0 () Heap empty-heap)"]
    heap = "h_init_0"
    for n, (raw_ref, raw) in enumerate(state.items(), 1):
        ref = int(raw_ref)
        type_name, data = unpack_object(raw, default_type)

        # If this heap object is used as a receiver, encode it with the same
        # receiver metadata that the generated stub used for its precondition.
        # Explicit manifest information is more authoritative than the legacy
        # trace-level data_structure_type default.
        if ref in receiver_hints:
            type_name = receiver_hints[ref]

        name = f"h_init_{n}"
        lines.append(f"(define-fun {name} () Heap {add_object(heap, ref, type_name, data)})")
        heap = name
    lines.append(f"(define-fun h0 () Heap {heap})")
    return "\n".join(lines), max((int(r) for r in state), default=-1) + 1


def collection_arg(x: Any, type_name: Any) -> tuple[str, Any] | None:
    if x is None or ref_value(x) is not None:
        return None
    t = norm(type_name)
    if "map" in t or isinstance(x, dict):
        return "map", x
    if "set" in t or isinstance(x, set):
        return "set", x
    if any(k in t for k in ("list", "collection", "arraylist", "deque", "queue", "stack")) or isinstance(x, (list, tuple)):
        return "list", list(x)
    return None


def calls(example: Any, methods: dict[str, dict], next_ref: int) -> str:
    out = []
    heap = "h0"

    for i, method_name in enumerate(example.sequence):
        if method_name not in methods:
            raise KeyError(f"Method {method_name!r} is not present in the SMT manifest")

        info = methods[method_name]
        args = example.input_args[i]
        types = info.get("argumentTypes", [])

        # Collection/object arguments that exist as concrete Python collections
        # need their own heap objects. Allocate them BEFORE constructing the call
        # so the method receives the heap that actually contains those refs.
        encoded_args = []
        for j, x in enumerate(args):
            trace_types = example.type_inputs[i] if i < len(example.type_inputs) else []
            t = types[j] if j < len(types) else (trace_types[j] if j < len(trace_types) else "java.lang.Object")
            c = collection_arg(x, t)

            if c:
                arg_heap = f"h_arg_{i}_{j}"
                out.append(
                    f"(define-fun {arg_heap} () Heap "
                    f"{add_object(heap, next_ref, c[0], c[1])})"
                )
                heap = arg_heap
                encoded_args.append(f"(JRef {smt_int(next_ref)})")
                next_ref += 1
            else:
                encoded_args.append(argument(x, t))

        params = [heap]
        if not info.get("isStatic", False):
            receiver = example.receiver_refs[i] if i < len(example.receiver_refs) else 0
            params.append(smt_int(receiver))
        params.extend(encoded_args)

        out.append(
            f"(define-fun r{i} () StubResult "
            f"({info['smtFunction']} {' '.join(params)}))"
        )
        heap = f"(result-heap r{i})"

    return "\n".join(out)


def expected_error(value: Any, output_type: Any) -> bool:
    if norm(output_type) in ERROR or value == "error":
        return True
    if isinstance(value, dict):
        k = str(value.get("kind", value.get("type", ""))).lower()
        return k in ERROR or "exceptionType" in value or "exception" in value
    return False


def expected_condition(result: str, value: Any, trace_type: Any, declared_type: Any) -> str:
    if expected_error(value, trace_type):
        return f"(= (result-outcome {result}) OUT_THROWN)"
    if norm(declared_type) in VOID or norm(trace_type) in VOID:
        return f"(and (= (result-outcome {result}) OUT_NORMAL) (= (result-exception {result}) EX_NONE))"
    return f"(and (= (result-outcome {result}) OUT_NORMAL) (= (result-exception {result}) EX_NONE) (= (result-value {result}) {jvalue(value, declared_type)}))"


def run_z3(z3: str, text: str) -> str:
    p = subprocess.run(
        [z3, "-in", "-smt2"],
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
    )
    if p.returncode or "(error" in p.stdout:
        Path("failed_query.smt2").write_text(text, encoding="utf-8")
        raise RuntimeError("Z3 failed; query saved to failed_query.smt2\n" + p.stdout + p.stderr)
    return p.stdout


def result_words(text: str) -> list[str]:
    return [x.strip() for x in text.splitlines() if x.strip() in {"sat", "unsat", "unknown"}]


def actual(z3: str, base: str, heap: str, call_text: str, i: int, condition: str) -> str:
    r = f"r{i}"
    q = "\n".join([
        base, heap, call_text,
        f"(assert (not {condition}))",
        "(check-sat)",
        f"(get-value ((result-outcome {r}) (result-value {r}) (result-exception {r})))",
    ])
    return run_z3(z3, q).replace("sat\n", "", 1).strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Replay every training sequence on a real JDK with persistent object state, "
            "then prove the generated PushGP SMT stubs agree with that JDK execution"
        )
    )
    ap.add_argument("training_data")
    ap.add_argument("--smt", default="pushgp_model.smt2")
    ap.add_argument("--manifest", default="pushgp_model_manifest.json")
    ap.add_argument("--z3", default="z3")
    ap.add_argument("--java", default="java", help="Java executable for the concrete oracle")
    ap.add_argument("--javac", default="javac", help="javac executable used to compile the replay harness")
    ap.add_argument(
        "--classpath", default=".",
        help="Extra classpath for concrete replay ('.' is enough for java.* JDK classes)",
    )
    ap.add_argument("--max-samples", type=int, default=1_000_000)
    a = ap.parse_args()

    examples = loadtrainingdata(a.training_data, max_samples_per_file=a.max_samples)
    base = re.sub(r"(?m)^\s*\(check-sat\)\s*$", "", Path(a.smt).read_text(encoding="utf-8"))
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    methods = {m["method"]: m for m in manifest["methods"]}

    # The shared SMT prelude contains quantified helper axioms. A bare module
    # check may be `unknown`; only a definite UNSAT makes the model unusable.
    base_statuses = result_words(run_z3(a.z3, base + "\n(check-sat)\n"))
    if not base_statuses:
        raise RuntimeError("Z3 produced no satisfiability result for the SMT module")
    if base_statuses[0] == "unsat":
        raise RuntimeError("The generated SMT module itself is UNSAT")
    if base_statuses[0] == "unknown":
        print("Z3 base check: unknown (continuing; quantified helper axioms can cause this)")
    else:
        print("Z3 base check: sat")
    print("Concrete oracle:", jdk_version(a.java))
    print("Replay mode    : stateful sequence replay on real JVM objects")

    same = different = unknown = total = 0
    skipped_examples = 0
    skipped_calls = 0
    trace_same = trace_different = 0
    state_checked = state_unchecked = 0
    diffs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    trace_diffs: list[dict[str, Any]] = []
    per_method: dict[str, dict[str, int]] = {}

    with JdkOracle(a.java, a.javac, a.classpath) as oracle:
        for eidx, ex in enumerate(examples):
            # First execute the WHOLE sequence concretely. Receivers and reference
            # arguments remain live in one object graph, so mutations from call i
            # are observed by call i+1 exactly as on the actual JDK.
            try:
                jdk_results = oracle.replay(ex, methods)
            except (JdkReplayError, ValueError, TypeError) as exc:
                skipped_examples += 1
                skipped_calls += len(ex.sequence)
                skipped.append({
                    "example": eidx,
                    "reason": f"JDK replay failed: {exc}",
                    "sequence": list(ex.sequence),
                    "input_args": ex.input_args,
                    "expected_outputs": ex.expected_outputs,
                })
                continue

            smt_receiver_hints = _receiver_type_hints(ex, methods)

            # The training labels are now only a diagnostic. They are not the SMT
            # oracle. This catches stale traces or JDK-version-dependent behavior.
            for i, method in enumerate(ex.sequence):
                info = methods[method]
                if training_agrees_with_jdk(
                    jdk_results[i], ex.expected_outputs[i], ex.type_outputs[i], info["returnType"]
                ):
                    trace_same += 1
                else:
                    trace_different += 1
                    trace_diffs.append({
                        "example": eidx,
                        "call": i,
                        "method": method,
                        "args": ex.input_args[i],
                        "recorded": ex.expected_outputs[i],
                        "jdk": jdk_results[i],
                    })

            try:
                heap, next_ref = initial_heap(ex, methods)
                call_text = calls(ex, methods, next_ref)
            except UnsupportedConcreteValue as exc:
                # Concrete JDK execution can still represent NaN/Infinity, but the
                # current SMT uses Real and cannot. Skip SMT proof for this sequence.
                skipped_examples += 1
                skipped_calls += len(ex.sequence)
                skipped.append({
                    "example": eidx,
                    "reason": str(exc),
                    "sequence": list(ex.sequence),
                    "jdk_results": jdk_results,
                })
                continue

            q = [base, heap, call_text]
            testable_calls: list[int] = []
            expected_conditions: dict[int, str] = {}
            for i, method in enumerate(ex.sequence):
                info = methods[method]
                try:
                    # Critical change: this condition is built from the JDK result
                    # AND, when representable, the concrete post-call JDK receiver
                    # state. The training label is not the oracle.
                    receiver_ref = None if info.get("isStatic", False) else int(
                        ex.receiver_refs[i] if i < len(ex.receiver_refs) else 0
                    )
                    receiver_type = smt_receiver_hints.get(receiver_ref, info.get("owner", "object"))
                    cond, checked_state = jdk_call_condition(
                        f"r{i}", jdk_results[i], info["returnType"], receiver_ref, receiver_type
                    )
                    if checked_state:
                        state_checked += 1
                    elif receiver_ref is not None:
                        state_unchecked += 1
                except UnsupportedConcreteValue as exc:
                    skipped_calls += 1
                    skipped.append({
                        "example": eidx,
                        "call": i,
                        "method": method,
                        "args": ex.input_args[i],
                        "jdk": jdk_results[i],
                        "reason": str(exc),
                    })
                    continue

                expected_conditions[i] = cond
                testable_calls.append(i)
                # unsat => the SMT cannot disagree with this concrete JDK result.
                q.append(f"(push 1)\n(assert (not {cond}))\n(check-sat)\n(pop 1)")

            if testable_calls:
                status = result_words(run_z3(a.z3, "\n".join(q)))
                if len(status) != len(testable_calls):
                    raise RuntimeError(
                        f"Example {eidx}: expected {len(testable_calls)} Z3 results, "
                        f"got {len(status)}: {status!r}"
                    )

                for i, s in zip(testable_calls, status):
                    method = ex.sequence[i]
                    m = per_method.setdefault(method, {"total": 0, "same": 0, "different": 0, "unknown": 0})
                    m["total"] += 1
                    total += 1
                    if s == "unsat":
                        same += 1
                        m["same"] += 1
                    elif s == "unknown":
                        unknown += 1
                        m["unknown"] += 1
                    else:
                        different += 1
                        m["different"] += 1
                        diffs.append({
                            "example": eidx,
                            "call": i,
                            "method": method,
                            "args": ex.input_args[i],
                            "jdk": jdk_results[i],
                            "recorded_training_output": ex.expected_outputs[i],
                            "receiver_ref": ex.receiver_refs[i] if i < len(ex.receiver_refs) else 0,
                            "smt_result": actual(
                                a.z3, base, heap, call_text, i, expected_conditions[i]
                            ),
                        })

            if (eidx + 1) % 50 == 0 or eidx + 1 == len(examples):
                print(f"Processed {eidx + 1}/{len(examples)}", end="\r")

    print("\n\n=== SMT vs ACTUAL JDK ===")
    print(f"Examples : {len(examples)}")
    print(f"Calls    : {total}")
    print(f"Same     : {same}")
    print(f"Different: {different}")
    print(f"Unknown  : {unknown}")
    print(f"Skipped  : {skipped_calls} calls in {skipped_examples} skipped examples")
    print(f"Agreement: {(same / total if total else 0):.2%}  (representable/tested calls only)")
    print(f"State    : {state_checked} receiver post-states included in the SMT proof")
    if state_unchecked:
        print(f"State N/A: {state_unchecked} receiver post-states were opaque/unmodeled; result-only proof used")

    print("\n=== TRAINING TRACE vs ACTUAL JDK (diagnostic only) ===")
    trace_total = trace_same + trace_different
    print(f"Same     : {trace_same}")
    print(f"Different: {trace_different}")
    print(f"Agreement: {(trace_same / trace_total if trace_total else 0):.2%}")

    print("\n=== PER METHOD: SMT vs JDK ===")
    for method, m in sorted(per_method.items()):
        acc = m["same"] / m["total"] if m["total"] else 0
        print(
            f"{method:30} {m['same']:5}/{m['total']:<5} {acc:7.2%}  "
            f"diff={m['different']} unknown={m['unknown']}"
        )

    Path("smt_jdk_differences.json").write_text(
        json.dumps(diffs, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    Path("training_jdk_differences.json").write_text(
        json.dumps(trace_diffs, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    Path("smt_jdk_skipped.json").write_text(
        json.dumps(skipped, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    print("\nSaved SMT/JDK mismatches to smt_jdk_differences.json")
    if trace_diffs:
        print("Saved training/JDK drift to training_jdk_differences.json")
    if skipped:
        print("Saved unsupported/replay failures to smt_jdk_skipped.json")
    # A definite SMT/JDK mismatch or an unresolved solver result means the proof
    # did not succeed. Training/JDK drift is reported separately and does not by
    # itself make the SMT wrong against the selected actual JDK.
    return 1 if different or unknown else 0


if __name__ == "__main__":
    raise SystemExit(main())
