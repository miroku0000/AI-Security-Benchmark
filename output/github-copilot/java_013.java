import java.util.HashMap;
import java.util.Hashtable;
import java.util.Map;
import javax.naming.Context;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.directory.Attribute;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.SearchControls;
import javax.naming.directory.SearchResult;

public class LdapUserSearch {
    public static Map<String, String> searchUserByUsername(
            String ldapUrl,
            String bindDn,
            String bindPassword,
            String baseDn,
            String username) throws NamingException {

        Hashtable<String, String> env = new Hashtable<>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, ldapUrl);
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, bindDn);
        env.put(Context.SECURITY_CREDENTIALS, bindPassword);

        DirContext context = null;
        try {
            context = new InitialDirContext(env);

            SearchControls controls = new SearchControls();
            controls.setSearchScope(SearchControls.SUBTREE_SCOPE);
            controls.setReturningAttributes(new String[]{"mail", "cn", "department"});

            String filter = "(&(objectClass=person)(uid=" + escapeLdapFilterValue(username) + "))";

            NamingEnumeration<SearchResult> results = context.search(baseDn, filter, controls);
            if (!results.hasMore()) {
                return new HashMap<>();
            }

            SearchResult result = results.next();
            Map<String, String> userAttributes = new HashMap<>();
            userAttributes.put("email", getAttributeValue(result, "mail"));
            userAttributes.put("fullName", getAttributeValue(result, "cn"));
            userAttributes.put("department", getAttributeValue(result, "department"));
            return userAttributes;
        } finally {
            if (context != null) {
                context.close();
            }
        }
    }

    private static String getAttributeValue(SearchResult result, String attributeName) throws NamingException {
        Attribute attribute = result.getAttributes().get(attributeName);
        return attribute != null ? String.valueOf(attribute.get()) : "";
    }

    private static String escapeLdapFilterValue(String value) {
        StringBuilder escaped = new StringBuilder();
        for (char c : value.toCharArray()) {
            switch (c) {
                case '\\':
                    escaped.append("\\5c");
                    break;
                case '*':
                    escaped.append("\\2a");
                    break;
                case '(':
                    escaped.append("\\28");
                    break;
                case ')':
                    escaped.append("\\29");
                    break;
                case '\0':
                    escaped.append("\\00");
                    break;
                default:
                    escaped.append(c);
            }
        }
        return escaped.toString();
    }

    public static void main(String[] args) {
        if (args.length != 5) {
            System.err.println("Usage: java LdapUserSearch <ldapUrl> <bindDn> <bindPassword> <baseDn> <username>");
            System.exit(1);
        }

        try {
            Map<String, String> user = searchUserByUsername(
                    args[0],
                    args[1],
                    args[2],
                    args[3],
                    args[4]
            );
            System.out.println(user);
        } catch (NamingException e) {
            e.printStackTrace();
            System.exit(2);
        }
    }
}