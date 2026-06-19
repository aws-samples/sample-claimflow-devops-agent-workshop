"""Frontend Stack — S3 deployment and CloudFront invalidation."""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    CfnOutput,
)
from constructs import Construct


class FrontendStack(Stack):
    """Frontend deployment — React SPA to S3 with CloudFront."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        frontend_bucket: s3.Bucket,
        frontend_distribution: cloudfront.Distribution,
        api_url: str,
        config_api_url: str = "",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Deploy frontend build artifacts to S3 + invalidate CloudFront.
        self.deployment = s3deploy.BucketDeployment(
            self,
            "DeployFrontend",
            sources=[s3deploy.Source.asset("../frontend/build")],
            destination_bucket=frontend_bucket,
            distribution=frontend_distribution,
            distribution_paths=["/*"],
        )

        # Inject the real API URL at deploy time by overwriting config.js in the
        # bucket. config_api_url MUST be a plain string (resolved by the pipeline
        # from CloudFormation), not a CDK token — tokens embedded in asset file
        # contents cannot be resolved and break template synthesis. When empty,
        # config.js is left as shipped (app falls back to its default).
        self.config_deployment = None
        if config_api_url:
            self.config_deployment = s3deploy.BucketDeployment(
                self,
                "DeployFrontendConfig",
                sources=[
                    s3deploy.Source.data(
                        "config.js",
                        f'window.__API_URL__ = "{config_api_url}";\n',
                    )
                ],
                destination_bucket=frontend_bucket,
                distribution=frontend_distribution,
                distribution_paths=["/config.js"],
                prune=False,
            )
            self.config_deployment.node.add_dependency(self.deployment)

        # Outputs
        CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{frontend_distribution.distribution_domain_name}",
            description="Frontend application URL",
        )

        CfnOutput(
            self,
            "ApiEndpoint",
            value=api_url,
            description="Backend API endpoint URL",
        )
