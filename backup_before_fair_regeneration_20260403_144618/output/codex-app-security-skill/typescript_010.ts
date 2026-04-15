import express, { type NextFunction, type Request, type Response } from 'express';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';
import axios, { AxiosError } from 'axios';
import { load } from 'cheerio';
import dns from 'node:dns/promises';
import net from 'node:net';