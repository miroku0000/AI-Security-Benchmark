func pingHandler(srv any, ctx context.Context, dec func(any) error, interceptor grpc.UnaryServerInterceptor) (any, error) {
	in := new(PingRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(*AuthService).Ping(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/auth.AuthService/Ping",
	}
	handler := func(ctx context.Context, req any) (any, error) {
		return srv.(*AuthService).Ping(ctx, req.(*PingRequest))
	}
	return interceptor(ctx, in, info, handler)
}