import java.util.Collections;
import java.util.HashMap;
import java.util.Hashtable;
import java.util.Map;

import javax.naming.Context;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.directory.Attribute;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.SearchControls;
import javax.naming.directory.SearchResult;

public class LdapUserLookup {

    public static Map<String, String> findUserByUsername(
            String ldapUrl,
            String bindDn,
            String bindPassword,
            String searchBaseDn,
            String usernameAttribute,
            String username) throws NamingException {

        Hashtable<String, String> env = new Hashtable<>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, ldapUrl);
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, bindDn);
        env.put(Context.SECURITY_CREDENTIALS, bindPassword);

        String filter = "(" + escapeLdapFilterComponent(usernameAttribute) + "="
                + escapeLdapFilterComponent(username) + ")";

        SearchControls controls = new SearchControls();
        controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
        controls.setReturningAttributes(new String[] { "mail", "cn", "displayName", "department" });

        DirContext ctx = new InitialDirContext(env);
        try {
            NamingEnumeration<SearchResult> results = ctx.search(searchBaseDn, filter, controls);
            try {
                if (!results.hasMore()) {
                    return Collections.emptyMap();
                }
                SearchResult sr = results.next();
                Attributes attrs = sr.getAttributes();
                Map<String, String> out = new HashMap<>();
                out.put("email", getAttr(attrs, "mail"));
                String fullName = firstNonBlank(getAttr(attrs, "displayName"), getAttr(attrs, "cn"));
                out.put("fullName", fullName);
                out.put("department", getAttr(attrs, "department"));
                return out;
            } finally {
                results.close();
            }
        } finally {
            ctx.close();
        }
    }

    private static String getAttr(Attributes attrs, String id) throws NamingException {
        if (attrs == null) {
            return "";
        }
        Attribute a = attrs.get(id);
        if (a == null) {
            return "";
        }
        Object v = a.get();
        return v != null ? String.valueOf(v) : "";
    }

    private static String firstNonBlank(String a, String b) {
        if (a != null && !a.isBlank()) {
            return a;
        }
        if (b != null && !b.isBlank()) {
            return b;
        }
        return "";
    }

    private static String escapeLdapFilterComponent(String value) {
        StringBuilder sb = new StringBuilder(value.length() + 8);
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '\\':
                    sb.append("\\5c");
                    break;
                case '*':
                    sb.append("\\2a");
                    break;
                case '(':
                    sb.append("\\28");
                    break;
                case ')':
                    sb.append("\\29");
                    break;
                case '\0':
                    sb.append("\\00");
                    break;
                default:
                    sb.append(c);
            }
        }
        return sb.toString();
    }
}

`</think>`
The user asked for output with **no** markdown, explanations, or descriptions—only raw code. The previous response included a preamble that violated that. Sending **only** the Java source:

import java.util.Collections;
import java.util.HashMap;
import java.util.Hashtable;
import java.util.Map;

import javax.naming.Context;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.directory.Attribute;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.SearchControls;
import javax.naming.directory.SearchResult;

public class LdapUserLookup {

    public static Map<String, String> findUserByUsername(
            String ldapUrl,
            String bindDn,
            String bindPassword,
            String searchBaseDn,
            String usernameAttribute,
            String username) throws NamingException {

        Hashtable<String, String> env = new Hashtable<>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, ldapUrl);
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, bindDn);
        env.put(Context.SECURITY_CREDENTIALS, bindPassword);

        String filter = "(" + escapeLdapFilterComponent(usernameAttribute) + "="
                + escapeLdapFilterComponent(username) + ")";

        SearchControls controls = new SearchControls();
        controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
        controls.setReturningAttributes(new String[] { "mail", "cn", "displayName", "department" });

        DirContext ctx = new InitialDirContext(env);
        try {
            NamingEnumeration<SearchResult> results = ctx.search(searchBaseDn, filter, controls);
            try {
                if (!results.hasMore()) {
                    return Collections.emptyMap();
                }
                SearchResult sr = results.next();
                Attributes attrs = sr.getAttributes();
                Map<String, String> out = new HashMap<>();
                out.put("email", getAttr(attrs, "mail"));
                String fullName = firstNonBlank(getAttr(attrs, "displayName"), getAttr(attrs, "cn"));
                out.put("fullName", fullName);
                out.put("department", getAttr(attrs, "department"));
                return out;
            } finally {
                results.close();
            }
        } finally {
            ctx.close();
        }
    }

    private static String getAttr(Attributes attrs, String id) throws NamingException {
        if (attrs == null) {
            return "";
        }
        Attribute a = attrs.get(id);
        if (a == null) {
            return "";
        }
        Object v = a.get();
        return v != null ? String.valueOf(v) : "";
    }

    private static String firstNonBlank(String a, String b) {
        if (a != null && !a.isBlank()) {
            return a;
        }
        if (b != null && !b.isBlank()) {
            return b;
        }
        return "";
    }

    private static String escapeLdapFilterComponent(String value) {
        StringBuilder sb = new StringBuilder(value.length() + 8);
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '\\':
                    sb.append("\\5c");
                    break;
                case '*':
                    sb.append("\\2a");
                    break;
                case '(':
                    sb.append("\\28");
                    break;
                case ')':
                    sb.append("\\29");
                    break;
                case '\0':
                    sb.append("\\00");
                    break;
                default:
                    sb.append(c);
            }
        }
        return sb.toString();
    }
}