# Social Media Service

Real-time monitoring and analysis of social media content for public safety.

## Features
- **Ingestion**: Collect publicly available content from social platforms
- **Monitoring**: Real-time content monitoring with AI analysis
- **Content Analysis**: NLP and computer vision analysis of posts/videos
- **Risk Flags**: Automatic flagging of potentially harmful content
- **Case Generation**: Create investigation cases from flagged content

## Supported Platforms
- YouTube
- Facebook
- Twitter/X
- Instagram
- Public web sources

## Detection Categories
- Violence and threats
- Hate speech and incitement
- Dangerous stunts (railway, road)
- Criminal activity documentation
- Unauthorized FIR/investigation leaks
- Fake news and misinformation

## Workflow
1. Content ingested from social platforms
2. AI analyzes content (NLP + CV + audio)
3. Risk score assigned (Low / Medium / High)
4. High-risk content → Alert to moderators
5. Moderator reviews and decides action
6. Evidence preserved for investigation if needed

## Port: 8005
