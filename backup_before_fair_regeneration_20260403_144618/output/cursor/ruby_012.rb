def initialize(app, options = {})
        @cookie_name = (options[:cookie_key] || :session).to_s
        super
      end

      private

      def load_session(request)
        sid = request.session_options[:id] || request.cookies[@key] || generate_sid
        raw = request.cookies[@cookie_name]
        data =
          if raw && !raw.empty?
            Marshal.load(Base64.decode64(raw))
          else
            {}
          end
        data = {} unless data.is_a?(Hash)
        [sid, data]
      rescue ArgumentError, TypeError, NameError
        [generate_sid, {}]
      end

      def commit_session(request, response)
        options = session_options_for_request(request)
        session = request.session
        sid = request.session_options[:id] || generate_sid

        if session.empty?
          response.delete_cookie(@cookie_name, cookie_options(options))
          response.delete_cookie(@key, cookie_options(options))
          return
        end

        value = Base64.encode64(Marshal.dump(session.to_hash))
        response.set_cookie(@cookie_name, cookie_options(options).merge(value: value))
        response.set_cookie(@key, cookie_options(options).merge(value: sid.to_s))
      end

      def cookie_options(options)
        {
          path: options[:path] || "/",
          domain: options[:domain],
          expires: options[:expire_after],
          secure: options[:secure],
          httponly: options[:httponly] != false,
          same_site: options[:same_site]
        }.compact
      end
    end
  end
end