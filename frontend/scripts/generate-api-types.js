#!/usr/bin/env node
/**
 * OpenAPI TypeScript Type Generator
 * 
 * Generates TypeScript types and a typed API client from the FastAPI OpenAPI schema.
 * This ensures the frontend is compile-time safe against backend changes.
 * 
 * Usage:
 *   npm run generate:api-types   # Uses backend at http://localhost:8000
 *   BACKEND_URL=http://prod.example.com npm run generate:api-types
 * 
 * What it generates:
 *   - src/api/schema.ts: TypeScript types for all request/response bodies
 *   - src/api/openapi.json: Snapshot of the OpenAPI schema (for CI diff detection)
 * 
 * Prerequisites:
 *   - Backend must be running to fetch /openapi.json
 *   - npm install openapi-typescript (already added to devDependencies)
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const OUTPUT_DIR = path.join(__dirname, '../src/api');
const SCHEMA_FILE = path.join(OUTPUT_DIR, 'schema.ts');
const OPENAPI_SNAPSHOT = path.join(OUTPUT_DIR, 'openapi.json');

async function main() {
  console.log('🔍 Fetching OpenAPI schema from', BACKEND_URL);
  
  try {
    // Fetch the OpenAPI schema
    const response = await fetch(`${BACKEND_URL}/openapi.json`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const schema = await response.json();
    
    // Save the OpenAPI snapshot for CI diff detection
    console.log('📝 Saving OpenAPI snapshot to', OPENAPI_SNAPSHOT);
    fs.writeFileSync(
      OPENAPI_SNAPSHOT, 
      JSON.stringify(schema, null, 2) + '\n',
      'utf8'
    );
    
    // Generate TypeScript types using openapi-typescript
    console.log('🔨 Generating TypeScript types...');
    execSync(
      `npx openapi-typescript ${OPENAPI_SNAPSHOT} -o ${SCHEMA_FILE}`,
      { stdio: 'inherit' }
    );
    
    console.log('✅ Generated TypeScript types at', SCHEMA_FILE);
    console.log('✅ OpenAPI snapshot saved at', OPENAPI_SNAPSHOT);
    
    // Show summary
    const typeContent = fs.readFileSync(SCHEMA_FILE, 'utf8');
    const typeCount = (typeContent.match(/export (type|interface)/g) || []).length;
    console.log(`📊 Generated ${typeCount} types/interfaces`);
    
  } catch (error) {
    if (error.code === 'ECONNREFUSED') {
      console.error('❌ Could not connect to backend at', BACKEND_URL);
      console.error('   Make sure the backend is running: cd backend && uvicorn app.main:app --reload');
      process.exit(1);
    }
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

main();
