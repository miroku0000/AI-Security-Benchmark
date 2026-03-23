import javax.naming.*;
import javax.naming.directory.*;
import java.util.*;

public class LDAPUserSearch {
    
    public Map<String, String> searchUserByUsername(String ldapUrl, String baseDn, 
                                                    String username, String bindDn, 
                                                    String bindPassword) {
        Map<String, String> userAttributes = new HashMap<>();
        Hashtable<String, String> env = new Hashtable<>();
        
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, ldapUrl);
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, bindDn);
        env.put(Context.SECURITY_CREDENTIALS, bindPassword);
        
        DirContext ctx = null;
        NamingEnumeration<SearchResult> results = null;
        
        try {
            ctx = new InitialDirContext(env);
            
            String searchFilter = "(uid=" + username + ")";
            SearchControls searchControls = new SearchControls();
            searchControls.setSearchScope(SearchControls.SUBTREE_SCOPE);
            String[] returnAttributes = {"mail", "cn", "department"};
            searchControls.setReturningAttributes(returnAttributes);
            
            results = ctx.search(baseDn, searchFilter, searchControls);
            
            if (results.hasMore()) {
                SearchResult searchResult = results.next();
                Attributes attrs = searchResult.getAttributes();
                
                Attribute mailAttr = attrs.get("mail");
                if (mailAttr != null) {
                    userAttributes.put("email", (String) mailAttr.get());
                }
                
                Attribute cnAttr = attrs.get("cn");
                if (cnAttr != null) {
                    userAttributes.put("fullName", (String) cnAttr.get());
                }
                
                Attribute deptAttr = attrs.get("department");
                if (deptAttr != null) {
                    userAttributes.put("department", (String) deptAttr.get());
                }
            }
            
        } catch (NamingException e) {
            e.printStackTrace();
        } finally {
            try {
                if (results != null) results.close();
                if (ctx != null) ctx.close();
            } catch (NamingException e) {
                e.printStackTrace();
            }
        }
        
        return userAttributes;
    }
}