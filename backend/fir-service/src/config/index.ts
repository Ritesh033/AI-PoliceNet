export const config = {
  port: parseInt(process.env.FIR_PORT || '8003', 10),
  postgres: {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
    database: process.env.POSTGRES_DB || 'ai_policenet',
    user: process.env.POSTGRES_USER || 'policenet_admin',
    password: process.env.POSTGRES_PASSWORD || 'changeme',
  },
  kafka: {
    brokers: (process.env.KAFKA_BROKERS || 'localhost:9092').split(','),
    clientId: 'fir-service',
  },
};
