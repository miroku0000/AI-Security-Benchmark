/* src/utils/secureAsyncStorage.ts */
import AsyncStorage from '@react-native-async-storage/async-storage';
import CryptoJS from 'crypto-js';
import { STORAGE_ENCRYPTION_KEY } from '../config/encryption';