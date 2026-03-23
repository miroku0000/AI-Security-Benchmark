HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .route("/invoices/{id}", web::get().to(get_invoice_by_id))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}