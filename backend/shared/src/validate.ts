import { Request, Response, NextFunction } from 'express';
import { ZodSchema, ZodError } from 'zod';
import { ApiError, ErrorCode } from './errors';

export function validateRequest(schema: ZodSchema, source: 'body' | 'query' | 'params' = 'body') {
  return (req: Request, _res: Response, next: NextFunction) => {
    try {
      const data = schema.parse(req[source]);
      req[source] = data;
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        next(
          new ApiError(ErrorCode.VALIDATION_ERROR, 'Validation failed', error.errors)
        );
      } else {
        next(error);
      }
    }
  };
}
