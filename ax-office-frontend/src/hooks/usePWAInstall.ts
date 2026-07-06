/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { useState, useEffect, useCallback } from 'react';

/**
 * Extended BeforeInstallPromptEvent type
 * The native type isn't exposed in standard TS lib
 */
interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

export interface UsePWAInstallReturn {
  /** Whether the app can be installed */
  canInstall: boolean;
  /** Whether the app is already installed (running as PWA) */
  isInstalled: boolean;
  /** Whether the install prompt was dismissed */
  isDismissed: boolean;
  /** Trigger the native install prompt */
  promptInstall: () => Promise<boolean>;
  /** Dismiss the install prompt (remember dismissal) */
  dismissInstall: () => void;
  /** Platform the install is available on */
  platform: string | null;
}

// LocalStorage key for remembering dismissal
const DISMISS_KEY = 'axbi-pwa-install-dismissed';

// Minimum time between showing prompts (7 days)
const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

/**
 * Hook to manage PWA installation state
 */
export function usePWAInstall(): UsePWAInstallReturn {
  const [deferredPrompt, setDeferredPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [platform, setPlatform] = useState<string | null>(null);

  useEffect(() => {
    // Check if already installed (running as PWA)
    const checkInstalled = () => {
      // Check display mode
      if (window.matchMedia('(display-mode: standalone)').matches) {
        return true;
      }
      // Check iOS standalone mode
      if ((window.navigator as any).standalone === true) {
        return true;
      }
      return false;
    };

    setIsInstalled(checkInstalled());

    // Listen for display mode changes
    const mediaQuery = window.matchMedia('(display-mode: standalone)');
    const handleChange = (e: MediaQueryListEvent) => {
      setIsInstalled(e.matches);
    };
    mediaQuery.addEventListener('change', handleChange);

    // Check if previously dismissed
    const dismissedAt = localStorage.getItem(DISMISS_KEY);
    if (dismissedAt) {
      const dismissTime = parseInt(dismissedAt, 10);
      if (Date.now() - dismissTime < DISMISS_DURATION_MS) {
        setIsDismissed(true);
      } else {
        // Clear expired dismissal
        localStorage.removeItem(DISMISS_KEY);
      }
    }

    // Listen for beforeinstallprompt event
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      const promptEvent = e as BeforeInstallPromptEvent;
      setDeferredPrompt(promptEvent);

      // Set platform info
      if (promptEvent.platforms.length > 0) {
        setPlatform(promptEvent.platforms[0]);
      }
    };

    // Listen for app installed event
    const handleAppInstalled = () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
      localStorage.removeItem(DISMISS_KEY);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener(
        'beforeinstallprompt',
        handleBeforeInstallPrompt,
      );
      window.removeEventListener('appinstalled', handleAppInstalled);
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<boolean> => {
    if (!deferredPrompt) {
      return false;
    }

    try {
      await deferredPrompt.prompt();

      const choiceResult = await deferredPrompt.userChoice;

      if (choiceResult.outcome === 'accepted') {
        setDeferredPrompt(null);
        setIsDismissed(false);
        return true;
      }

      return false;
    } catch (error) {
      console.error('PWA install prompt failed:', error);
      return false;
    }
  }, [deferredPrompt]);

  const dismissInstall = useCallback(() => {
    setIsDismissed(true);
    localStorage.setItem(DISMISS_KEY, Date.now().toString());
  }, []);

  return {
    canInstall: deferredPrompt !== null && !isInstalled && !isDismissed,
    isInstalled,
    isDismissed,
    promptInstall,
    dismissInstall,
    platform,
  };
}

export default usePWAInstall;
