import argparse, json, time, subprocess
import boto3
from botocore.exceptions import ClientError 

def resolve_queue_url(args, sqs):
    if args.queue_url:
        return args.queue_url
    if args.from_tf:
        return subprocess.check_output(
            ["terraform", "output", "-raw", "queue_url"], text=True
        ).strip()
    if args.queue_name:
        try:
            return sqs.get_queue_url(QueueName=args.queue_name) ["QueueUrl"]
        except ClientError as e:
            raise SystemExit(f"[Error] get_queue_url: {e}")
    raise SystemExit("Provide --queue-url, --queue-name, or --from-tf.")

def cmd_send(args):
    sqs = boto3.client("sqs", region_name=args.region)
    qurl = resolve_queue_url(args, sqs)
    body = json.dumps({"msg": args.message, "ts": int(time.time())})
    try:
        sqs.send_message(
            QueueUrl=qurl,
            MessageBody=body,
            MessageAttributes={
                "env": {"DataType": "String", "StringValue": args.env},
                "source": {"DataType": "String", "StringValue": "sqs-demo"},
            },
        )
        print(f"Sent: {body}")

        if args.batch > 0:
            entries = []
            for i in range(min(args.batch, 10)):  # SQS batch max 10
                entries.append({
                    "Id": f"m{i}",
                    "MessageBody": json.dumps({"msg": f"{args.message}-{i}", "ts": int(time.time())}),
                })
            resp = sqs.send_message_batch(QueueUrl=qurl, Entries=entries)
            ok = len(resp.get("Successful", []))
            print(f"Batch sent: {ok} / {len(entries)}")
    except ClientError as e:
        print(f"[ERROR] send: {e}")

def cmd_recv(args):
    sqs = boto3.client("sqs", region_name=args.region)
    qurl = resolve_queue_url(args, sqs)
    total = 0
    try:
        while total < args.max:
            resp = sqs.receive_message(
                QueueUrl=qurl,
                MaxNumberOfMessages=min(10, args.max - total),
                WaitTimeSeconds=10,            # long polling
                VisibilityTimeout=args.vtimeout
            )
            msgs = resp.get("Messages", [])
            if not msgs:
                print("(no messages)")
                break
            for m in msgs:
                total += 1
                body = m["Body"]
                print(f"\nReceived: {body}")
                # delete after "processing"
                if args.delete:
                    sqs.delete_message(QueueUrl=qurl, ReceiptHandle=m["ReceiptHandle"])
                    print("  -> deleted")
                else:
                    print("  -> not deleted (will reappear after visibility timeout)")
            if total >= args.max:
                break
    except ClientError as e:
        print(f"[ERROR] receive: {e}")

def cmd_purge(args):
    sqs = boto3.client("sqs", region_name=args.region)
    qurl = resolve_queue_url(args, sqs)
    try:
        sqs.purge_queue(QueueUrl=qurl)
        print("Purge requested (may take up to 60s).")
    except ClientError as e:
        print(f"[ERROR] purge: {e} (note: only once per 60s)")

def main():
    ap = argparse.ArgumentParser(description="SQS demo: send, receive, purge")
    ap.add_argument("--region", default=None, help="AWS region (inherits env/profile if omitted)")
    ap.add_argument("--queue-url", help="Queue URL")
    ap.add_argument("--queue-name", help="Queue name")
    ap.add_argument("--from-tf", action="store_true", help="Read queue URL from terraform output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("send")
    sp.add_argument("--message", default="hello from boto3", help="Message text")
    sp.add_argument("--env", default="dev")
    sp.add_argument("--batch", type=int, default=0, help="Also send N extra messages (max 10)")
    sp.set_defaults(func=cmd_send)

    sp = sub.add_parser("recv")
    sp.add_argument("--max", type=int, default=5, help="Max messages to fetch")
    sp.add_argument("--vtimeout", type=int, default=30, help="Visibility timeout seconds")
    sp.add_argument("--delete", action="store_true", help="Delete after processing")
    sp.set_defaults(func=cmd_recv)

    sp = sub.add_parser("purge")
    sp.set_defaults(func=cmd_purge)

    args = ap.parse_args()
    args.func(args)
