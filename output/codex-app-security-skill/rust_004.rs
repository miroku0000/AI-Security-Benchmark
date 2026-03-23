HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .wrap(
                DefaultHeaders::new()
                    .add((header::X_CONTENT_TYPE_OPTIONS, "nosniff"))
                    .add((header::CACHE_CONTROL, "private, no-store"))
                    .add((header::X_FRAME_OPTIONS, "DENY"))
                    .add((header::REFERRER_POLICY, "no-referrer")),
            )
            .route("/uploads/{filename}", web::get().to(serve_upload))
    })
    .bind((host.as_str(), port))?
    .run()
    .await
}