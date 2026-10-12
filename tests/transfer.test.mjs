import test from 'node:test';
import assert from 'node:assert/strict';
import {encodePhoto} from '../src/transfer.mjs';

test('encodes JPEG blob to JSON-compatible base64',async()=>{
  const bytes = new Uint8Array([0xff,0xd8,0xff,0x00,0x01]);
  const blob=new Blob([bytes],{type:'image/jpeg'});
  const value=await encodePhoto(blob);
  assert.deepEqual(new Uint8Array(Buffer.from(value,'base64')),bytes);
});
test('rejects unsupported media and oversize photos',async()=>{
  await assert.rejects(()=>encodePhoto(new Blob([new Uint8Array([1,2,3])],{type:'text/plain'})),/Cannot transfer/);
  await assert.rejects(()=>encodePhoto(new Blob([new Uint8Array(3 * 1024 * 1024 + 1)],{type:'image/jpeg'})),/Cannot transfer/);
});
