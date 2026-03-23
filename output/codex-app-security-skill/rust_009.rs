HttpServer::new(move || {
        App::new()
            .wrap(Logger::default())
            .app_data(web::Data::new(pool.clone()))
            .app_data(
                web::PathConfig::default()
                    .error_handler(|_, _| AppError::BadRequest("invalid invoice id").into()),
            )
            .route("/invoices/{id}", web::get().to(get_invoice))
    })
    .bind(bind_addr)?
    .run()
    .await
}