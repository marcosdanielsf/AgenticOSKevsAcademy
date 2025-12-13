# Google OAuth Setup Instructions

## 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the Google+ API and Google Identity Services
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set application type to "Web application"
6. Add authorized origins:
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
7. Add authorized redirect URIs:
   - `http://localhost:3000/auth/google/callback`
8. Copy the Client ID and Client Secret

## 2. Update Environment Variables

Update your `.env` file with the actual Google OAuth credentials:

```
GOOGLE_CLIENT_ID=your_actual_google_client_id
GOOGLE_CLIENT_SECRET=your_actual_google_client_secret
```

## 3. Update HTML File

In `index.html`, replace `YOUR_GOOGLE_CLIENT_ID` with your actual Google Client ID:

```html
data-client_id="your_actual_google_client_id"
```

## 4. Test the Implementation

1. Open `index.html` in a web browser
2. Click the "Sign in with Google" button
3. Complete the OAuth flow
4. User information should display after successful sign-in

## 5. For Production

- Update authorized origins and redirect URIs to match your production domain
- Use HTTPS in production
- Store environment variables securely
- Never expose Client Secret in frontend code

## Security Notes

- The Client Secret should only be used in backend/server-side code
- The frontend implementation uses the Google Identity Services library for secure token handling
- ID tokens are JWT tokens that contain user information
- Always validate tokens on your backend before trusting the user data