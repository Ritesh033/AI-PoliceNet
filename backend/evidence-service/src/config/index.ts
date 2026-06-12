export const config = {
  port: parseInt(process.env.EVIDENCE_PORT || '8004', 10),
  postgres: {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
    database: process.env.POSTGRES_DB || 'ai_policenet',
    user: process.env.POSTGRES_USER || 'policenet_admin',
    password: process.env.POSTGRES_PASSWORD || 'changeme',
  },
  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/ai_policenet',
  },
  kafka: {
    brokers: (process.env.KAFKA_BROKERS || 'localhost:9092').split(','),
  },
  evidence: {
    maxFileSizeMB: 500,
    reviewPeriodDays: 5,
    permanentThreshold: 3, // Number of uploads needed for auto-permanent
    allowedTypes: ['video/mp4', 'video/avi', 'video/quicktime', 'video/webm',
      'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4',
      'image/jpeg', 'image/png', 'image/bmp', 'image/tiff',
      'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  },
  s3: {
    bucket: process.env.S3_EVIDENCE_BUCKET || 'ai-policenet-evidence',
    region: process.env.AWS_REGION || 'ap-south-1',
  },
};
