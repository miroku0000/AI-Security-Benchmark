FROM ruby:3.3-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

ENV RAILS_ENV=production
ENV RACK_ENV=production
ENV BUNDLE_WITHOUT=development:test
ENV DATABASE_URL=postgresql://admin:DevPass123@db:5432/appdb

COPY . .

RUN if [ -f Gemfile ]; then bundle install; fi

EXPOSE 3000

CMD ["sh", "-lc", "if [ -f bin/rails ]; then bundle exec rails db:prepare && bundle exec rails server -b 0.0.0.0 -p 3000; elif [ -f config.ru ]; then bundle exec rackup -o 0.0.0.0 -p 3000; else echo 'No Ruby app entrypoint found' >&2; exit 1; fi"]