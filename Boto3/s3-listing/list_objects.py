import argparse
import boto3
from botocore.exceptions import ClientError

def list_objects(bucket: str, prefix: str | None = None):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    total = 0
    total_size = 0
    newest = None
    largest = (None, 0)

    print(f"Bucket: {bucket}")
    if prefix: 
        print(f"Prefix: {prefix}")

    try: 
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix or "")
        found_any = False
        for page in pages:
            contents = page.get("Contents", [])
            if contents:
                found_any = True
            for obj in contents:
                key = obj["Key"]
                size = obj["Size"]
                lm = obj["LastModified"]
                total += 1
                total_size += size
                if newest is None or lm > newest[1]:
                    newest = (key, lm)
                    if size > largest[1]:
                        largest = (key, size)
                    print(key)
        if not found_any:
            print("(no objects found)")
        print("\nSummary")
        print("-------")
        print(f"Object count : {total}")
        print(f"Total size   : {total_size} bytes")
        if newest:
            print(f"Newest object: {newest[0]} @ {newest[1]}")
        if largest[0]:
            print(f"Largest obj  : {largest[0]} ({largest[1]} bytes)")
    except ClientError as e:
        print(f"[ERROR] {e}")

def main():
    ap = argparse.ArgumentParser(description="List objects in an S3 bucket.")
    ap.add_argument("--bucket", help="S3 bucket name")
    ap.add_argument("--prefix", help="Optional key prefix", default=None)
    ap.add_argument("--region", help="AWS region (optional)", default=None)
    ap.add_argument("--from-tf", action="store_true",
                    help="Read bucket name from `terraform output -raw bucket_name`")
    args = ap.parse_args()

    if args.from_tf and not args.bucket:
        import subprocess
        args.bucket = subprocess.check_output(
            ["terraform", "output", "-raw", "bucket_name"], text=True
        ).strip()

    if not args.bucket:
        print("Provide --bucket <name> (or use --from-tf).")
        return

    if args.region:
        boto3.setup_default_session(region_name=args.region)

    list_objects(args.bucket, args.prefix)

if __name__ == "__main__":
    main()