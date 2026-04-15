final class Secure_User_Authentication_Plugin {
	private const LOGIN_ACTION = 'sua_login';
	private const REGISTER_ACTION = 'sua_register';
	private const FLASH_QUERY_ARG = 'sua_notice';
	private const FLASH_ERROR_ARG = 'sua_error';
	private const RATE_LIMIT_MAX_ATTEMPTS = 5;
	private const RATE_LIMIT_WINDOW = 900;