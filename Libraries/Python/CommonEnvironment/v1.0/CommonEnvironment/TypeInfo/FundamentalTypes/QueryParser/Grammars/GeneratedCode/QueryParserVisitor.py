# Generated from C:\Temp\QueryParser\Grammars\BuildEnvironment\..\QueryParser.g4 by ANTLR 4.7
from antlr4 import *

# This class defines a complete generic visitor for a parse tree produced by QueryParserParser.

class QueryParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by QueryParserParser#statements.
    def visitStatements(self, ctx):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by QueryParserParser#statement.
    def visitStatement(self, ctx):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by QueryParserParser#expression.
    def visitExpression(self, ctx):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by QueryParserParser#value.
    def visitValue(self, ctx):
        return self.visitChildren(ctx)


