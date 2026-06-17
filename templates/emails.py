"""
Email templates for CVS lead generation.
All templates are personalized by the Outreach Agent using Claude.
"""

from config import config


def initial_outreach(
    first_name: str,
    company: str,
    title: str,
    pain_point: str,  # AI-generated, specific to their company
    personalized_line: str,  # AI-generated opener
) -> tuple[str, str]:
    """Returns (subject, html_body)."""
    subject = f"Quick question about {company}'s {pain_point}"
    html = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<p>Hi {first_name},</p>

<p>{personalized_line}</p>

<p>I'm reaching out because we've been helping <strong>B2B SaaS companies and teams building custom CRMs</strong>
cut their development time by 40-60% — without sacrificing quality or flexibility.</p>

<p>At <strong>{config.COMPANY_NAME}</strong>, we specialize in:</p>
<ul>
  <li>✅ Custom CRM development tailored to your sales workflow</li>
  <li>✅ SaaS product development from MVP to scale</li>
  <li>✅ Integrations (Salesforce, HubSpot, Pipedrive, and custom APIs)</li>
</ul>

<p>I'd love to show you what we've built for similar companies —
<a href="{config.COMPANY_PORTFOLIO_URL}" style="color: #4F46E5;">see our portfolio here</a>.</p>

<p>Would a <strong>15-minute demo call</strong> this week make sense?
<a href="{config.CALENDLY_MEETING_LINK}" style="background: #4F46E5; color: white; padding: 8px 16px;
border-radius: 4px; text-decoration: none; display: inline-block; margin-top: 8px;">
→ Book a time here</a></p>

<p>Best,<br>
<strong>{config.SENDER_NAME}</strong><br>
{config.COMPANY_NAME}<br>
<a href="{config.COMPANY_WEBSITE}">{config.COMPANY_WEBSITE}</a></p>

<p style="font-size: 11px; color: #999;">
If this isn't relevant, just reply "unsubscribe" and I won't reach out again.
</p>
</body></html>
"""
    return subject, html


def follow_up(
    first_name: str,
    company: str,
    original_subject: str,
    value_prop: str,  # AI-generated, different angle from first email
) -> tuple[str, str]:
    """Returns (subject, html_body) for follow-up email."""
    subject = f"Re: {original_subject}"
    html = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<p>Hi {first_name},</p>

<p>Just wanted to bump this up in case it got buried. {value_prop}</p>

<p>I know you're busy running {company}, so I'll keep this short:</p>

<p>We recently helped a SaaS company similar to yours <strong>reduce their CRM customization costs by 55%</strong>
while shipping 3x faster. I think we could do the same for your team.</p>

<p>Here's a quick demo of what we built:
<a href="{config.COMPANY_DEMO_URL}" style="color: #4F46E5;">Watch 2-min demo →</a></p>

<p>If the timing is right, grab 15 minutes on my calendar:<br>
<a href="{config.CALENDLY_MEETING_LINK}" style="color: #4F46E5;">{config.CALENDLY_MEETING_LINK}</a></p>

<p>If not now, no worries — I'll check back in a few weeks.</p>

<p>Best,<br>
<strong>{config.SENDER_NAME}</strong><br>
{config.COMPANY_NAME}</p>
</body></html>
"""
    return subject, html


def meeting_confirmation(
    first_name: str,
    company: str,
) -> tuple[str, str]:
    """Returns (subject, html_body) for post-reply meeting booking email."""
    subject = f"Let's connect, {first_name} — here's my calendar"
    html = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<p>Hi {first_name},</p>

<p>Thanks for getting back to me! I'd love to learn more about {company}
and share how {config.COMPANY_NAME} might be able to help.</p>

<p>Feel free to grab any 15 or 30-minute slot that works for you:</p>

<p style="text-align: center; margin: 24px 0;">
<a href="{config.CALENDLY_MEETING_LINK}"
   style="background: #4F46E5; color: white; padding: 12px 24px;
   border-radius: 6px; text-decoration: none; font-size: 16px; display: inline-block;">
📅 Book a Meeting
</a></p>

<p>Before our call, here are a few resources that might be useful:</p>
<ul>
  <li><a href="{config.COMPANY_PORTFOLIO_URL}" style="color: #4F46E5;">Our Portfolio</a> — recent CRM & SaaS projects</li>
  <li><a href="{config.COMPANY_DEMO_URL}" style="color: #4F46E5;">Product Demo</a> — 2-minute walkthrough</li>
  <li><a href="{config.COMPANY_WEBSITE}" style="color: #4F46E5;">About {config.COMPANY_NAME}</a></li>
</ul>

<p>Looking forward to talking!</p>

<p>Best,<br>
<strong>{config.SENDER_NAME}</strong><br>
{config.COMPANY_NAME}</p>
</body></html>
"""
    return subject, html
