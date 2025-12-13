class GoogleAuth {
    constructor(clientId) {
        this.clientId = clientId;
        this.isSignedIn = false;
        this.currentUser = null;
    }

    async initialize() {
        try {
            await this.loadGoogleScript();
            google.accounts.id.initialize({
                client_id: this.clientId,
                callback: this.handleCredentialResponse.bind(this)
            });
            console.log('Google Auth initialized');
        } catch (error) {
            console.error('Failed to initialize Google Auth:', error);
        }
    }

    loadGoogleScript() {
        return new Promise((resolve, reject) => {
            if (window.google && window.google.accounts) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://accounts.google.com/gsi/client';
            script.async = true;
            script.defer = true;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    handleCredentialResponse(response) {
        try {
            const userInfo = this.decodeJwtToken(response.credential);
            this.currentUser = {
                idToken: response.credential,
                profile: userInfo
            };
            this.isSignedIn = true;
            
            this.onSignIn(this.currentUser);
            console.log('User signed in:', userInfo);
        } catch (error) {
            console.error('Error handling credential response:', error);
        }
    }

    decodeJwtToken(token) {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            window.atob(base64)
                .split('')
                .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    }

    renderSignInButton(elementId, options = {}) {
        const defaultOptions = {
            type: 'standard',
            shape: 'rectangular',
            theme: 'outline',
            text: 'signin_with',
            size: 'large',
            logo_alignment: 'left'
        };

        const config = { ...defaultOptions, ...options };
        
        google.accounts.id.renderButton(
            document.getElementById(elementId),
            config
        );
    }

    signOut() {
        if (this.isSignedIn) {
            google.accounts.id.disableAutoSelect();
            this.currentUser = null;
            this.isSignedIn = false;
            this.onSignOut();
            console.log('User signed out');
        }
    }

    // Override these methods in your implementation
    onSignIn(user) {
        // Default implementation - override this
        console.log('Sign in successful:', user);
    }

    onSignOut() {
        // Default implementation - override this
        console.log('Sign out successful');
    }

    // Utility methods
    getCurrentUser() {
        return this.currentUser;
    }

    isUserSignedIn() {
        return this.isSignedIn;
    }

    getUserProfile() {
        return this.currentUser ? this.currentUser.profile : null;
    }

    getIdToken() {
        return this.currentUser ? this.currentUser.idToken : null;
    }
}

// Example usage:
// const auth = new GoogleAuth('YOUR_GOOGLE_CLIENT_ID');
// auth.onSignIn = function(user) {
//     document.getElementById('user-info').innerHTML = `Welcome, ${user.profile.name}!`;
// };
// auth.onSignOut = function() {
//     document.getElementById('user-info').innerHTML = '';
// };
// auth.initialize();