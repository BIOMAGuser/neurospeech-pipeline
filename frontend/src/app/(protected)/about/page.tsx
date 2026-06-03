"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronLeft, BrainCircuit, Shield, Server, Scale, Users } from "lucide-react";
import { version, appName } from "@/lib/version";

export default function AboutPage() {
  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div className="flex items-center gap-3">
        <Link href="/">
          <Button variant="ghost" size="icon">
            <ChevronLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Info</h1>
          <p className="text-slate-500 text-sm">Neurolingo / {appName} v{version}</p>
        </div>
      </div>

      {/* About */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BrainCircuit className="h-5 w-5 text-blue-600" />
            Neurolingo
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Neurolingo ist eine Plattform zur KI-gestuetzten neuropsychologischen Sprachanalyse.
            Das System unterstuetzt klinisches Fachpersonal bei der Aufnahme, Transkription und
            automatisierten Auswertung von Sprachproben im Rahmen standardisierter diagnostischer Verfahren.
          </p>
          <p>
            Die Anwendung umfasst drei Aufgabentypen: semantische Fluenz (Gemuese), Sprichwort-Ergaenzung
            und Bildbeschreibung (Cookie Theft Picture). Die Ergebnisse werden als strukturierte Metriken
            bereitgestellt und koennen im HL7 FHIR R4 Format exportiert werden.
          </p>
        </CardContent>
      </Card>

      {/* Autoren */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-5 w-5 text-teal-600" />
            Autoren
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600 leading-relaxed">
          <ul className="space-y-1">
            <li><span className="font-medium text-slate-800">Stefan Brodoehl</span></li>
            <li><span className="font-medium text-slate-800">Lydia Justi</span></li>
          </ul>
          <p className="mt-3 text-slate-500">
            Universitaetsklinikum Jena, Klinik fuer Neurologie
          </p>
        </CardContent>
      </Card>

      {/* Technologie */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Server className="h-5 w-5 text-indigo-600" />
            Technologie
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600 leading-relaxed">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <dt className="text-slate-500 text-xs uppercase tracking-wide">Frontend</dt>
              <dd className="font-medium text-slate-700">Next.js, React, TypeScript, Tailwind CSS</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs uppercase tracking-wide">Backend</dt>
              <dd className="font-medium text-slate-700">FastAPI, Python, SQLAlchemy, SQLite</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs uppercase tracking-wide">Spracherkennung</dt>
              <dd className="font-medium text-slate-700">OpenAI Whisper</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs uppercase tracking-wide">Textanalyse</dt>
              <dd className="font-medium text-slate-700">OpenAI GPT-4, spaCy NLP</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs uppercase tracking-wide">Datenaustausch</dt>
              <dd className="font-medium text-slate-700">HL7 FHIR R4</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs uppercase tracking-wide">Infrastruktur</dt>
              <dd className="font-medium text-slate-700">Docker, Nginx</dd>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Datenschutz */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-5 w-5 text-emerald-600" />
            Datenschutz
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Alle Patientendaten werden ausschliesslich lokal auf dem Server gespeichert (SQLite-Datenbank).
            Es erfolgt keine Weitergabe von Patientendaten an Dritte.
          </p>
          <p>
            Audiodateien werden zur Transkription an die OpenAI Whisper API uebermittelt.
            Die Transkripte werden anschliessend zur Analyse an die OpenAI GPT API gesendet.
            Gemaess der OpenAI-Nutzungsrichtlinien werden API-Eingaben nicht fuer das Training
            von Modellen verwendet.
          </p>
          <p>
            Benutzerspezifische OpenAI API-Keys werden mit Fernet-Verschluesselung in einer
            separaten Datenbank gespeichert. Die Authentifizierung erfolgt ueber JWT-Tokens.
          </p>
        </CardContent>
      </Card>

      {/* Disclaimer */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Scale className="h-5 w-5 text-amber-600" />
            Haftungsausschluss
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Neurolingo ist ein Forschungswerkzeug zur Unterstuetzung der klinischen Diagnostik.
            Die Ergebnisse der automatisierten Sprachanalyse dienen ausschliesslich als
            ergaenzende Information und ersetzen keine aerztliche Diagnose oder Befundung.
          </p>
          <p>
            Die Richtigkeit und Vollstaendigkeit der KI-generierten Analysen kann nicht
            garantiert werden. Die klinische Interpretation und Bewertung obliegt dem
            behandelnden Fachpersonal.
          </p>
          <p>
            Die Software wird ohne Gewaehrleistung bereitgestellt. Die Autoren uebernehmen
            keine Haftung fuer Schaeden, die aus der Nutzung der Software entstehen.
          </p>
        </CardContent>
      </Card>

      {/* Copyright Footer */}
      <div className="text-center text-xs text-slate-400 pt-4 pb-8 border-t border-slate-200">
        &copy; {new Date().getFullYear()} Stefan Brodoehl, Lydia Justi. Alle Rechte vorbehalten.
      </div>
    </div>
  );
}
