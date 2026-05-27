import { headers } from 'next/headers';
import { Webhook } from 'svix';
import type { WebhookEvent } from '@clerk/nextjs/server';
import { db } from '@/lib/db';

export async function POST(req: Request) {
  const secret = process.env.CLERK_WEBHOOK_SECRET;
  if (!secret) {
    return new Response('CLERK_WEBHOOK_SECRET is not set', { status: 500 });
  }

  const headerPayload = headers();
  const svixId = headerPayload.get('svix-id');
  const svixTimestamp = headerPayload.get('svix-timestamp');
  const svixSignature = headerPayload.get('svix-signature');

  if (!svixId || !svixTimestamp || !svixSignature) {
    return new Response('Missing Svix headers', { status: 400 });
  }

  const payload = await req.text();
  const wh = new Webhook(secret);

  let evt: WebhookEvent;
  try {
    evt = wh.verify(payload, {
      'svix-id': svixId,
      'svix-timestamp': svixTimestamp,
      'svix-signature': svixSignature,
    }) as WebhookEvent;
  } catch (err) {
    console.error('Invalid Clerk webhook signature', err);
    return new Response('Invalid signature', { status: 400 });
  }

  try {
    switch (evt.type) {
      case 'user.created':
      case 'user.updated': {
        const { id: clerkId, email_addresses, first_name, last_name } = evt.data;
        const primaryEmailId = evt.data.primary_email_address_id;
        const primary =
          email_addresses.find((e) => e.id === primaryEmailId) ?? email_addresses[0];
        const email = primary?.email_address;
        if (!email) return new Response('No email on user', { status: 400 });

        const name = [first_name, last_name].filter(Boolean).join(' ') || null;

        await db.user.upsert({
          where: { clerkId },
          update: { email, name },
          create: { clerkId, email, name },
        });
        break;
      }

      case 'user.deleted': {
        const clerkId = evt.data.id;
        if (!clerkId) break;
        await db.user.updateMany({
          where: { clerkId },
          data: { deletedAt: new Date() },
        });
        break;
      }

      default:
        // ignore other event types
        break;
    }
  } catch (err) {
    console.error('Clerk webhook handler error', err);
    return new Response('Internal error', { status: 500 });
  }

  return new Response('ok', { status: 200 });
}
