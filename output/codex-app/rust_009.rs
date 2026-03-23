HttpServer::new(move || {
        App::new()
            .app_data(Data::new(pool.clone()))
            .wrap_fn(|mut req, srv| {
                req.extensions_mut().insert(AuthenticatedUser { id: 42 });
                srv.call(req)
            })
            .route("/invoices/{id}", web::get().to(get_invoice_by_id))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}