from __future__ import annotations

from .enums import (
    AuthenticationType,
    Capability,
    Category,
    RefreshFrequency,
    SourceType,
)
from .models import TrustedKnowledgeSource


OFFICIAL_DOCS: list[dict] = [
    {"id": "openai", "name": "OpenAI", "url": "https://platform.openai.com/docs", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.CHANGELOGS], "tags": ["llm", "api"]},
    {"id": "anthropic", "name": "Anthropic", "url": "https://docs.anthropic.com", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.CHANGELOGS], "tags": ["llm", "safety"]},
    {"id": "google-deepmind", "name": "Google DeepMind", "url": "https://deepmind.google/discover/blog/", "trust_score": 0.96, "priority": 85, "capabilities": [Capability.BLOG_POSTS, Capability.DOCUMENTATION], "tags": ["research", "multimodal"]},
    {"id": "meta-ai", "name": "Meta AI", "url": "https://ai.meta.com/blog/", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.BLOG_POSTS, Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["llm", "research"]},
    {"id": "microsoft-ai", "name": "Microsoft AI", "url": "https://learn.microsoft.com/en-us/ai/", "trust_score": 0.94, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["cloud", "enterprise"]},
    {"id": "nvidia-ai", "name": "NVIDIA", "url": "https://developer.nvidia.com/ai", "trust_score": 0.94, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["hardware", "cuda"]},
    {"id": "huggingface", "name": "Hugging Face", "url": "https://huggingface.co/docs", "trust_score": 0.96, "priority": 85, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.RELEASES], "tags": ["models", "community"]},
    {"id": "langchain", "name": "LangChain", "url": "https://python.langchain.com/docs", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.CHANGELOGS], "tags": ["framework", "agents"]},
    {"id": "crewai", "name": "CrewAI", "url": "https://docs.crewai.com", "trust_score": 0.88, "priority": 75, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["framework", "agents"]},
    {"id": "llamaindex", "name": "LlamaIndex", "url": "https://docs.llamaindex.ai", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.CHANGELOGS], "tags": ["framework", "rag"]},
    {"id": "dspy", "name": "DSPy", "url": "https://dspy-docs.vercel.app", "trust_score": 0.88, "priority": 75, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["framework", "programming"]},
    {"id": "pytorch", "name": "PyTorch", "url": "https://pytorch.org/docs/stable/", "trust_score": 0.97, "priority": 88, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.RELEASES], "tags": ["framework", "deep-learning"]},
    {"id": "tensorflow", "name": "TensorFlow", "url": "https://www.tensorflow.org/api_docs", "trust_score": 0.96, "priority": 85, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE, Capability.RELEASES], "tags": ["framework", "deep-learning"]},
    {"id": "onnx", "name": "ONNX", "url": "https://onnx.ai/docs/", "trust_score": 0.92, "priority": 78, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["format", "interoperability"]},
    {"id": "openvino", "name": "OpenVINO", "url": "https://docs.openvino.ai", "trust_score": 0.90, "priority": 76, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["hardware", "optimization"]},
    {"id": "aws-bedrock", "name": "AWS Bedrock", "url": "https://docs.aws.amazon.com/bedrock/", "trust_score": 0.93, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["cloud", "managed"]},
    {"id": "azure-ai", "name": "Azure AI", "url": "https://learn.microsoft.com/en-us/azure/ai-services/", "trust_score": 0.93, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["cloud", "managed"]},
    {"id": "vertex-ai", "name": "Vertex AI", "url": "https://cloud.google.com/vertex-ai/docs", "trust_score": 0.93, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.API_REFERENCE], "tags": ["cloud", "managed"]},
]

GITHUB_ORGS: list[dict] = [
    {"id": "github-openai", "name": "OpenAI (GitHub)", "url": "https://github.com/openai", "api_endpoint": "https://api.github.com/orgs/openai", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["llm", "api"]},
    {"id": "github-anthropic", "name": "Anthropic (GitHub)", "url": "https://github.com/anthropics", "api_endpoint": "https://api.github.com/orgs/anthropics", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["llm", "safety"]},
    {"id": "github-google", "name": "Google (GitHub)", "url": "https://github.com/google", "api_endpoint": "https://api.github.com/orgs/google", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["research"]},
    {"id": "github-deepmind", "name": "Google DeepMind (GitHub)", "url": "https://github.com/google-deepmind", "api_endpoint": "https://api.github.com/orgs/google-deepmind", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["research", "multimodal"]},
    {"id": "github-microsoft", "name": "Microsoft (GitHub)", "url": "https://github.com/microsoft", "api_endpoint": "https://api.github.com/orgs/microsoft", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["research", "cloud"]},
    {"id": "github-huggingface", "name": "Hugging Face (GitHub)", "url": "https://github.com/huggingface", "api_endpoint": "https://api.github.com/orgs/huggingface", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["models", "community"]},
    {"id": "github-langchain", "name": "LangChain (GitHub)", "url": "https://github.com/langchain-ai", "api_endpoint": "https://api.github.com/orgs/langchain-ai", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["framework", "agents"]},
    {"id": "github-llamaindex", "name": "LlamaIndex (GitHub)", "url": "https://github.com/run-llama", "api_endpoint": "https://api.github.com/orgs/run-llama", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["framework", "rag"]},
    {"id": "github-crewai", "name": "CrewAI (GitHub)", "url": "https://github.com/crewAIInc", "api_endpoint": "https://api.github.com/orgs/crewAIInc", "trust_score": 0.88, "priority": 75, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["framework", "agents"]},
    {"id": "github-ollama", "name": "Ollama (GitHub)", "url": "https://github.com/ollama", "api_endpoint": "https://api.github.com/orgs/ollama", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["llm", "local"]},
    {"id": "github-vllm", "name": "vLLM (GitHub)", "url": "https://github.com/vllm-project", "api_endpoint": "https://api.github.com/orgs/vllm-project", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["llm", "inference"]},
    {"id": "github-ggerganov", "name": "ggerganov (GitHub)", "url": "https://github.com/ggerganov", "api_endpoint": "https://api.github.com/orgs/ggerganov", "trust_score": 0.88, "priority": 75, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["llm", "cpp"]},
    {"id": "github-openmmlab", "name": "OpenMMLab (GitHub)", "url": "https://github.com/OpenMMLab", "api_endpoint": "https://api.github.com/orgs/OpenMMLab", "trust_score": 0.88, "priority": 74, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["vision", "research"]},
    {"id": "github-pytorch", "name": "PyTorch (GitHub)", "url": "https://github.com/pytorch", "api_endpoint": "https://api.github.com/orgs/pytorch", "trust_score": 0.97, "priority": 88, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["framework", "deep-learning"]},
    {"id": "github-tensorflow", "name": "TensorFlow (GitHub)", "url": "https://github.com/tensorflow", "api_endpoint": "https://api.github.com/orgs/tensorflow", "trust_score": 0.96, "priority": 85, "capabilities": [Capability.REPOSITORIES, Capability.RELEASES], "tags": ["framework", "deep-learning"]},
]

YOUTUBE_CHANNELS: list[dict] = [
    {"id": "yt-openai", "name": "OpenAI", "url": "https://youtube.com/@OpenAI", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.VIDEOS], "tags": ["llm", "official"]},
    {"id": "yt-anthropic", "name": "Anthropic", "url": "https://youtube.com/@AnthropicAI", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.VIDEOS], "tags": ["llm", "safety"]},
    {"id": "yt-deepmind", "name": "Google DeepMind", "url": "https://youtube.com/@GoogleDeepMind", "trust_score": 0.96, "priority": 85, "capabilities": [Capability.VIDEOS], "tags": ["research", "multimodal"]},
    {"id": "yt-nvidia", "name": "NVIDIA Developer", "url": "https://youtube.com/@NVIDIADeveloper", "trust_score": 0.94, "priority": 82, "capabilities": [Capability.VIDEOS], "tags": ["hardware", "cuda"]},
    {"id": "yt-msft-dev", "name": "Microsoft Developer", "url": "https://youtube.com/@MicrosoftDeveloper", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.VIDEOS], "tags": ["cloud", "enterprise"]},
    {"id": "yt-google-dev", "name": "Google for Developers", "url": "https://youtube.com/@googledevelopers", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.VIDEOS], "tags": ["cloud", "android"]},
    {"id": "yt-huggingface", "name": "Hugging Face", "url": "https://youtube.com/@HuggingFace", "trust_score": 0.94, "priority": 82, "capabilities": [Capability.VIDEOS], "tags": ["models", "community"]},
    {"id": "yt-two-minute-papers", "name": "Two Minute Papers", "url": "https://youtube.com/@TwoMinutePapers", "trust_score": 0.85, "priority": 72, "capabilities": [Capability.VIDEOS], "tags": ["research", "education"]},
    {"id": "yt-yannic-kilcher", "name": "Yannic Kilcher", "url": "https://youtube.com/@YannicKilcher", "trust_score": 0.86, "priority": 73, "capabilities": [Capability.VIDEOS], "tags": ["research", "news"]},
    {"id": "yt-karpathy", "name": "Andrej Karpathy", "url": "https://youtube.com/@AndrejKarpathy", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.VIDEOS], "tags": ["education", "deep-learning"]},
    {"id": "yt-deeplearning-ai", "name": "DeepLearningAI", "url": "https://youtube.com/@Deeplearningai", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.VIDEOS], "tags": ["education", "course"]},
    {"id": "yt-assemblyai", "name": "AssemblyAI", "url": "https://youtube.com/@AssemblyAI", "trust_score": 0.84, "priority": 70, "capabilities": [Capability.VIDEOS], "tags": ["speech", "research"]},
    {"id": "yt-arize-ai", "name": "Arize AI", "url": "https://youtube.com/@ArizeAI", "trust_score": 0.82, "priority": 68, "capabilities": [Capability.VIDEOS], "tags": ["observability", "monitoring"]},
    {"id": "yt-wandb", "name": "Weights & Biases", "url": "https://youtube.com/@WeightsBiases", "trust_score": 0.86, "priority": 72, "capabilities": [Capability.VIDEOS], "tags": ["mlops", "experiment"]},
    {"id": "yt-ibm-tech", "name": "IBM Technology", "url": "https://youtube.com/@IBMTechnology", "trust_score": 0.88, "priority": 74, "capabilities": [Capability.VIDEOS], "tags": ["enterprise", "cloud"]},
]

RESEARCH: list[dict] = [
    {"id": "arxiv", "name": "arXiv", "url": "https://arxiv.org", "api_endpoint": "http://export.arxiv.org/api/query", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["papers", "preprint"]},
    {"id": "semantic-scholar", "name": "Semantic Scholar", "url": "https://www.semanticscholar.org", "api_endpoint": "https://api.semanticscholar.org/graph/v1", "trust_score": 0.93, "priority": 83, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["papers", "search"]},
    {"id": "openreview", "name": "OpenReview", "url": "https://openreview.net", "trust_score": 0.90, "priority": 80, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["papers", "peer-review"]},
    {"id": "acl-anthology", "name": "ACL Anthology", "url": "https://aclanthology.org", "trust_score": 0.94, "priority": 82, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["nlp", "papers"]},
    {"id": "ieee-xplore", "name": "IEEE Xplore", "url": "https://ieeexplore.ieee.org", "trust_score": 0.94, "priority": 82, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["papers", "engineering"]},
    {"id": "acm-digital-library", "name": "ACM Digital Library", "url": "https://dl.acm.org", "trust_score": 0.94, "priority": 82, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["papers", "computing"]},
    {"id": "papers-with-code", "name": "Papers With Code", "url": "https://paperswithcode.com", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.RESEARCH_PAPERS, Capability.BENCHMARKS], "tags": ["papers", "benchmarks"]},
]

CONFERENCES: list[dict] = [
    {"id": "neurips", "name": "NeurIPS", "url": "https://neurips.cc", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "top-tier"]},
    {"id": "icml", "name": "ICML", "url": "https://icml.cc", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "top-tier"]},
    {"id": "iclr", "name": "ICLR", "url": "https://iclr.cc", "trust_score": 0.97, "priority": 88, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "top-tier"]},
    {"id": "cvpr", "name": "CVPR", "url": "https://cvpr.thecvf.com", "trust_score": 0.97, "priority": 88, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "vision"]},
    {"id": "eccv", "name": "ECCV", "url": "https://eccv.ecva.net", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "vision"]},
    {"id": "iccv", "name": "ICCV", "url": "https://iccv.thecvf.com", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "vision"]},
    {"id": "acl", "name": "ACL", "url": "https://aclweb.org", "trust_score": 0.97, "priority": 87, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "nlp"]},
    {"id": "emnlp", "name": "EMNLP", "url": "https://emnlp.org", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "nlp"]},
    {"id": "naacl", "name": "NAACL", "url": "https://naacl.org", "trust_score": 0.95, "priority": 84, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "nlp"]},
    {"id": "siggraph", "name": "SIGGRAPH", "url": "https://www.siggraph.org", "trust_score": 0.95, "priority": 84, "capabilities": [Capability.RESEARCH_PAPERS], "tags": ["conference", "graphics"]},
]

BLOGS: list[dict] = [
    {"id": "blog-openai", "name": "OpenAI Blog", "url": "https://openai.com/blog", "rss_feed": "https://openai.com/blog/feed.xml", "trust_score": 0.98, "priority": 90, "capabilities": [Capability.BLOG_POSTS], "tags": ["llm", "research"]},
    {"id": "blog-anthropic", "name": "Anthropic News", "url": "https://www.anthropic.com/news", "trust_score": 0.97, "priority": 88, "capabilities": [Capability.BLOG_POSTS], "tags": ["llm", "safety"]},
    {"id": "blog-google-ai", "name": "Google AI Blog", "url": "https://ai.googleblog.com", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.BLOG_POSTS], "tags": ["research", "llm"]},
    {"id": "blog-deepmind", "name": "DeepMind Blog", "url": "https://deepmind.google/discover/blog/", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.BLOG_POSTS], "tags": ["research", "multimodal"]},
    {"id": "blog-microsoft-ai", "name": "Microsoft AI Blog", "url": "https://blogs.microsoft.com/ai/", "trust_score": 0.94, "priority": 84, "capabilities": [Capability.BLOG_POSTS], "tags": ["research", "cloud"]},
    {"id": "blog-nvidia", "name": "NVIDIA Developer Blog", "url": "https://developer.nvidia.com/blog", "trust_score": 0.93, "priority": 82, "capabilities": [Capability.BLOG_POSTS], "tags": ["hardware", "cuda"]},
    {"id": "blog-aws-ml", "name": "AWS ML Blog", "url": "https://aws.amazon.com/blogs/machine-learning/", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.BLOG_POSTS], "tags": ["cloud", "mlops"]},
    {"id": "blog-huggingface", "name": "Hugging Face Blog", "url": "https://huggingface.co/blog", "trust_score": 0.94, "priority": 84, "capabilities": [Capability.BLOG_POSTS], "tags": ["models", "community"]},
    {"id": "blog-meta-ai", "name": "Meta AI Blog", "url": "https://ai.meta.com/blog/", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.BLOG_POSTS], "tags": ["research", "llm"]},
]

SOCIAL: list[dict] = [
    {"id": "x-openai", "name": "OpenAI (X)", "url": "https://x.com/OpenAI", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["llm", "official"]},
    {"id": "x-anthropic", "name": "Anthropic (X)", "url": "https://x.com/AnthropicAI", "trust_score": 0.88, "priority": 76, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["llm", "safety"]},
    {"id": "x-deepmind", "name": "Google DeepMind (X)", "url": "https://x.com/GoogleDeepMind", "trust_score": 0.86, "priority": 74, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["research", "multimodal"]},
    {"id": "x-huggingface", "name": "Hugging Face (X)", "url": "https://x.com/huggingface", "trust_score": 0.88, "priority": 76, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["models", "community"]},
    {"id": "x-msft-ai", "name": "Microsoft AI (X)", "url": "https://x.com/MSFTAI", "trust_score": 0.84, "priority": 72, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["research", "cloud"]},
    {"id": "x-nvidia", "name": "NVIDIA (X)", "url": "https://x.com/nvidia", "trust_score": 0.84, "priority": 72, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["hardware", "gpu"]},
    {"id": "x-meta-ai", "name": "Meta AI (X)", "url": "https://x.com/MetaAI", "trust_score": 0.85, "priority": 73, "capabilities": [Capability.SOCIAL_POSTS], "tags": ["research", "llm"]},
]

BENCHMARKS: list[dict] = [
    {"id": "artificial-analysis", "name": "Artificial Analysis", "url": "https://artificialanalysis.ai", "trust_score": 0.88, "priority": 76, "capabilities": [Capability.BENCHMARKS], "tags": ["benchmark", "llm"]},
    {"id": "lmsys-chatbot-arena", "name": "LMSYS Chatbot Arena", "url": "https://chat.lmsys.org", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.BENCHMARKS], "tags": ["benchmark", "llm"]},
    {"id": "mlperf", "name": "MLPerf", "url": "https://mlperf.org", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.BENCHMARKS], "tags": ["benchmark", "hardware"]},
    {"id": "hf-open-llm-leaderboard", "name": "Hugging Face Open LLM Leaderboard", "url": "https://huggingface.co/spaces/open-llm-leaderboard", "trust_score": 0.90, "priority": 78, "capabilities": [Capability.BENCHMARKS], "tags": ["benchmark", "llm"]},
    {"id": "papers-with-code-benchmarks", "name": "Papers With Code Benchmarks", "url": "https://paperswithcode.com/sota", "trust_score": 0.88, "priority": 76, "capabilities": [Capability.BENCHMARKS], "tags": ["benchmark", "sota"]},
]

PACKAGE_REGISTRIES: list[dict] = [
    {"id": "pypi", "name": "PyPI", "url": "https://pypi.org", "api_endpoint": "https://pypi.org/pypi", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.PACKAGES], "tags": ["python", "packages"]},
    {"id": "npm", "name": "npm", "url": "https://www.npmjs.com", "api_endpoint": "https://registry.npmjs.org", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.PACKAGES], "tags": ["javascript", "packages"]},
    {"id": "docker-hub", "name": "Docker Hub", "url": "https://hub.docker.com", "trust_score": 0.94, "priority": 84, "capabilities": [Capability.PACKAGES], "tags": ["containers", "images"]},
    {"id": "conda-forge", "name": "Conda Forge", "url": "https://conda-forge.org", "api_endpoint": "https://api.anaconda.org", "trust_score": 0.92, "priority": 80, "capabilities": [Capability.PACKAGES], "tags": ["python", "packages"]},
    {"id": "hf-models", "name": "Hugging Face Models", "url": "https://huggingface.co/models", "api_endpoint": "https://huggingface.co/api/models", "trust_score": 0.96, "priority": 86, "capabilities": [Capability.PACKAGES, Capability.REPOSITORIES], "tags": ["models", "community"]},
]

HARDWARE_VENDORS: list[dict] = [
    {"id": "hw-nvidia", "name": "NVIDIA", "url": "https://www.nvidia.com", "trust_score": 0.95, "priority": 85, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "gpu"]},
    {"id": "hw-amd", "name": "AMD", "url": "https://www.amd.com", "trust_score": 0.90, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "gpu"]},
    {"id": "hw-intel", "name": "Intel", "url": "https://www.intel.com", "trust_score": 0.90, "priority": 80, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "cpu"]},
    {"id": "hw-apple", "name": "Apple", "url": "https://www.apple.com", "trust_score": 0.92, "priority": 82, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "silicon"]},
    {"id": "hw-qualcomm", "name": "Qualcomm", "url": "https://www.qualcomm.com", "trust_score": 0.88, "priority": 78, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "mobile"]},
    {"id": "hw-arm", "name": "ARM", "url": "https://www.arm.com", "trust_score": 0.88, "priority": 78, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "architecture"]},
    {"id": "hw-renesas", "name": "Renesas", "url": "https://www.renesas.com", "trust_score": 0.82, "priority": 72, "capabilities": [Capability.DOCUMENTATION, Capability.RELEASES], "tags": ["hardware", "embedded"]},
]


OTHER: list[dict] = [
    {"id": "news-ai", "name": "AI News", "url": "https://example.com/ai-news", "trust_score": 0.70, "priority": 50, "capabilities": [Capability.BLOG_POSTS], "tags": ["news", "general"]},
    {"id": "podcast-ai", "name": "AI Podcast", "url": "https://example.com/ai-podcast", "trust_score": 0.70, "priority": 50, "capabilities": [Capability.VIDEOS], "tags": ["podcast", "general"]},
]


def get_seed_sources() -> list[TrustedKnowledgeSource]:
    sources: list[TrustedKnowledgeSource] = []

    for entry in OFFICIAL_DOCS:
        sources.append(_build(entry, SourceType.DOCUMENTATION, Category.LLM))

    for entry in GITHUB_ORGS:
        sources.append(_build(entry, SourceType.GITHUB, Category.TOOLING))

    for entry in YOUTUBE_CHANNELS:
        sources.append(_build(entry, SourceType.YOUTUBE, Category.LLM))

    for entry in RESEARCH:
        sources.append(_build(entry, SourceType.RESEARCH, Category.BENCHMARK))

    for entry in CONFERENCES:
        sources.append(_build(entry, SourceType.CONFERENCE, Category.BENCHMARK))

    for entry in BLOGS:
        sources.append(_build(entry, SourceType.BLOG, Category.LLM))

    for entry in SOCIAL:
        sources.append(_build(entry, SourceType.SOCIAL, Category.LLM))

    for entry in BENCHMARKS:
        sources.append(_build(entry, SourceType.BENCHMARK, Category.BENCHMARK))

    for entry in PACKAGE_REGISTRIES:
        sources.append(_build(entry, SourceType.PACKAGE_REGISTRY, Category.TOOLING))

    for entry in HARDWARE_VENDORS:
        sources.append(_build(entry, SourceType.HARDWARE_VENDOR, Category.HARDWARE))

    for entry in OTHER:
        st = SourceType.NEWS if "news" in entry["id"] else SourceType.PODCAST
        cat = Category.LLM
        sources.append(_build(entry, st, cat))

    return sources


def _build(entry: dict, source_type: SourceType, category: Category) -> TrustedKnowledgeSource:
    kwargs = dict(entry)
    kwargs["source_type"] = source_type
    kwargs["category"] = kwargs.get("category", category)
    kwargs["capabilities"] = frozenset(kwargs.get("capabilities", []))
    kwargs["tags"] = frozenset(kwargs.get("tags", []))
    return TrustedKnowledgeSource(**kwargs)
