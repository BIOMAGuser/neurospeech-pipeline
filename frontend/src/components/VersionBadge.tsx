import { Badge } from "@/components/ui/badge";
import { version, appName } from "@/lib/version";

interface VersionBadgeProps {
  className?: string;
}

export function VersionBadge({ className = "" }: VersionBadgeProps) {
  return (
    <Badge 
      variant="outline" 
      className={`text-xs text-muted-foreground bg-muted/50 ${className}`}
    >
      {appName} v{version}
    </Badge>
  );
}

interface VersionInfoProps {
  className?: string;
}

export function VersionInfo({ className = "" }: VersionInfoProps) {
  return (
    <div className={`text-xs text-muted-foreground ${className}`}>
      {appName} v{version}
    </div>
  );
}
